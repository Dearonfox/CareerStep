import json
import re
import zlib

from fastapi import APIRouter, Depends
from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional, require_admin
from app.models import Job, Profile, SavedJob, User
from app.schemas import JobCreate, JobRead, MatchBadge
from app.services.badge_scorer import best_badge_for_positions, score_job

router = APIRouter()


def build_profile_ctx(profile: Profile | None) -> dict | None:
    """배지 계산에 필요한 최소 프로필 컨텍스트를 추출한다."""
    if profile is None:
        return None
    return {
        "skills": json.loads(profile.skills) if profile.skills else [],
        "desired_role": profile.desired_role or "",
    }


def compact_text(value: object, max_length: int = 180) -> str:
    text_value = str(value or "")
    text_value = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text_value)
    text_value = re.sub(r"https?://\S+", " ", text_value)
    text_value = re.sub(r"[#>*_`|\\]+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if len(text_value) <= max_length:
        return text_value
    return text_value[:max_length].rstrip() + "..."


def choose_primary_position(relevant_positions: list, profile_ctx: dict | None = None) -> dict:
    positions = [position for position in relevant_positions if isinstance(position, dict)]
    if not positions:
        return {}
    if profile_ctx is None:
        return positions[0]

    user_skills = {str(skill).strip().lower() for skill in profile_ctx.get("skills", []) if str(skill).strip()}
    desired_role = str(profile_ctx.get("desired_role", "")).replace(" ", "").lower()

    def position_score(position: dict) -> tuple[int, int]:
        tech_stack = position.get("tech_stack") if isinstance(position.get("tech_stack"), list) else []
        tech_skills = {str(skill).strip().lower() for skill in tech_stack if str(skill).strip()}
        overlap = len(user_skills.intersection(tech_skills))
        title = str(position.get("position_title", "")).replace(" ", "").lower()
        role_hit = 1 if desired_role and (desired_role in title or title in desired_role) else 0
        return overlap, role_hit

    return max(positions, key=position_score)


def serialize_job(job: Job, profile_ctx: dict | None = None) -> JobRead:
    skills = json.loads(job.skills)
    badge = None
    if profile_ctx is not None:
        # MySQL 폴백 공고에는 routed_roles 가 없어 overlap 점수만 계산된다.
        result = score_job(profile_ctx["skills"], profile_ctx["desired_role"], [], skills)
        badge = MatchBadge(**result)
    return JobRead(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        employment_type=job.employment_type,
        skills=skills,
        description=job.description,
        match_badge=badge,
    )


def serialize_mongo_job(job: dict, profile_ctx: dict | None = None) -> JobRead:
    meta = job.get("meta") if isinstance(job.get("meta"), dict) else {}
    summary = job.get("summary") if isinstance(job.get("summary"), dict) else {}
    relevant_positions = summary.get("relevant_positions") if isinstance(summary.get("relevant_positions"), list) else []
    primary_position = choose_primary_position(relevant_positions, profile_ctx)

    raw_id = str(job.get("job_id") or job.get("_id") or "")
    job_id = int(raw_id) if raw_id.isdigit() else zlib.crc32(raw_id.encode("utf-8"))
    skills = primary_position.get("tech_stack") if isinstance(primary_position.get("tech_stack"), list) else []
    if not skills and isinstance(job.get("tags"), list):
        skills = job["tags"]

    main_tasks = primary_position.get("main_tasks", []) if isinstance(primary_position.get("main_tasks"), list) else []
    requirements = primary_position.get("requirements", []) if isinstance(primary_position.get("requirements"), list) else []
    description = compact_text(" ".join([*main_tasks[:2], *requirements[:2]]) or job.get("detail_markdown", ""))

    card_skills = [str(skill) for skill in skills if str(skill).strip()][:5]

    badge = None
    if profile_ctx is not None:
        routed_roles = summary.get("routed_roles") if isinstance(summary.get("routed_roles"), list) else []
        positions_tech_stacks = [
            p.get("tech_stack", [])
            for p in relevant_positions
            if isinstance(p, dict) and isinstance(p.get("tech_stack"), list) and p.get("tech_stack")
        ]
        if not positions_tech_stacks:
            positions_tech_stacks = [card_skills]
        result = best_badge_for_positions(
            profile_ctx["skills"], profile_ctx["desired_role"], routed_roles, positions_tech_stacks
        )
        badge = MatchBadge(**result)

    return JobRead(
        id=job_id,
        title=str(job.get("title") or primary_position.get("position_title") or "제목 없음"),
        company=str(job.get("company_name") or "회사명 없음"),
        location=str(primary_position.get("location") or meta.get("location") or "지역 미정"),
        employment_type=str(meta.get("employment_type") or primary_position.get("experience_level") or "고용형태 미정"),
        skills=card_skills,
        description=description or "MongoDB에 수집된 실제 채용공고입니다.",
        match_badge=badge,
    )


def list_mongo_jobs(profile_ctx: dict | None = None, limit: int = 60) -> list[JobRead]:
    if not settings.mongodb_uri:
        return []

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
        collection = client["careerstep"]["job_raw"]
        query = {"status": "routed"}
        if collection.count_documents(query, limit=1) == 0:
            query = {}

        cursor = collection.find(query).sort(
            [("scraped_at", DESCENDING), ("inserted_at", DESCENDING), ("_id", DESCENDING)]
        ).limit(limit)
        return [serialize_mongo_job(job, profile_ctx) for job in cursor]
    except (PyMongoError, ServerSelectionTimeoutError):
        return []
    finally:
        client.close()


def _sort_by_badge(jobs: list[JobRead]) -> list[JobRead]:
    return sorted(
        jobs,
        key=lambda j: j.match_badge.score if j.match_badge else -1,
        reverse=True,
    )


@router.get("", response_model=list[JobRead])
def list_jobs(
    sort: str | None = None,
    limit: int = 60,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> list[JobRead]:
    profile = (
        db.scalar(select(Profile).where(Profile.user_id == current_user.id))
        if current_user
        else None
    )
    profile_ctx = build_profile_ctx(profile)

    safe_limit = max(1, min(limit, 200))

    mongo_jobs = list_mongo_jobs(profile_ctx, limit=safe_limit)
    if mongo_jobs:
        return _sort_by_badge(mongo_jobs) if sort == "match" else mongo_jobs

    jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(safe_limit)).all()
    result = [serialize_job(job, profile_ctx) for job in jobs]
    return _sort_by_badge(result) if sort == "match" else result


@router.post("", response_model=JobRead)
def create_job(
    payload: JobCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JobRead:
    job = Job(
        title=payload.title,
        company=payload.company,
        location=payload.location,
        employment_type=payload.employment_type,
        skills=json.dumps(payload.skills, ensure_ascii=False),
        description=payload.description,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return serialize_job(job)


@router.post("/{job_id}/save")
def save_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    exists = db.scalar(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    if not exists:
        db.add(SavedJob(user_id=current_user.id, job_id=job_id))
        db.commit()
    return {"message": "saved"}
