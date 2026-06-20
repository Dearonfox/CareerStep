import json
import zlib

from fastapi import APIRouter, Depends
from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Job, SavedJob, User
from app.schemas import JobCreate, JobRead

router = APIRouter()


def serialize_job(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        employment_type=job.employment_type,
        skills=json.loads(job.skills),
        description=job.description,
    )


def serialize_mongo_job(job: dict) -> JobRead:
    meta = job.get("meta") if isinstance(job.get("meta"), dict) else {}
    summary = job.get("summary") if isinstance(job.get("summary"), dict) else {}
    relevant_positions = summary.get("relevant_positions") if isinstance(summary.get("relevant_positions"), list) else []
    primary_position = relevant_positions[0] if relevant_positions and isinstance(relevant_positions[0], dict) else {}

    raw_id = str(job.get("job_id") or job.get("_id") or "")
    job_id = int(raw_id) if raw_id.isdigit() else zlib.crc32(raw_id.encode("utf-8"))
    skills = job.get("tags") if isinstance(job.get("tags"), list) else []
    if not skills and isinstance(primary_position.get("tech_stack"), list):
        skills = primary_position["tech_stack"]

    description_parts = [
        job.get("detail_markdown", ""),
        primary_position.get("position_title", ""),
        " ".join(primary_position.get("main_tasks", []) if isinstance(primary_position.get("main_tasks"), list) else []),
        job.get("detail_url", ""),
    ]

    return JobRead(
        id=job_id,
        title=str(job.get("title") or primary_position.get("position_title") or "제목 없음"),
        company=str(job.get("company_name") or "회사명 없음"),
        location=str(primary_position.get("location") or meta.get("location") or "지역 미정"),
        employment_type=str(meta.get("employment_type") or primary_position.get("experience_level") or "고용형태 미정"),
        skills=[str(skill) for skill in skills if str(skill).strip()][:8],
        description="\n".join(part for part in description_parts if part).strip(),
    )


def list_mongo_jobs(limit: int = 60) -> list[JobRead]:
    if not settings.mongodb_uri:
        return []

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
        collection = client["careerstep"]["job_raw"]
        query = {
            "$or": [
                {"status": {"$in": ["summarized", "detailed", "pending"]}},
                {"status": {"$exists": False}},
            ]
        }
        cursor = collection.find(query).sort(
            [("scraped_at", DESCENDING), ("inserted_at", DESCENDING), ("_id", DESCENDING)]
        ).limit(limit)
        return [serialize_mongo_job(job) for job in cursor]
    except (PyMongoError, ServerSelectionTimeoutError):
        return []
    finally:
        client.close()


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobRead]:
    mongo_jobs = list_mongo_jobs()
    if mongo_jobs:
        return mongo_jobs

    jobs = db.scalars(select(Job).order_by(Job.created_at.desc())).all()
    return [serialize_job(job) for job in jobs]


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
