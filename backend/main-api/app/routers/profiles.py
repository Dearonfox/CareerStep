import io
import json

import pdfplumber
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import logging
from app.core.database import get_db
from app.deps import get_current_user
from app.models import Profile, User
from app.schemas import PortfolioTextRequest, ProfileRead, ProfileUpsert, TranscriptTextRequest
from app.services.ai_client import post_to_ai_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=ProfileRead | None)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile | None:
    return db.scalar(select(Profile).where(Profile.user_id == current_user.id))


@router.put("/me", response_model=ProfileRead)
async def upsert_my_profile(
    payload: ProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    values = {
        "desired_role": payload.desired_role,
        "skills": json.dumps(payload.skills, ensure_ascii=False),
        "certificates": json.dumps(payload.certificates, ensure_ascii=False),
        "projects": json.dumps(payload.projects, ensure_ascii=False),
    }
    if profile:
        for key, value in values.items():
            setattr(profile, key, value)
    else:
        profile = Profile(user_id=current_user.id, **values)
        db.add(profile)
    db.commit()
    db.refresh(profile)

    await _trigger_async_recommendation(current_user.id, profile)
    return profile


@router.post("/me/resume", response_model=ProfileRead)
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="PDF 파일만 업로드 가능합니다.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="파일 크기는 10MB 이하여야 합니다.")

    resume_text = _extract_text_from_pdf(contents)
    if not resume_text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="PDF에서 텍스트를 추출할 수 없습니다. 이미지 전용 PDF는 지원하지 않습니다.")

    parsed = await post_to_ai_service("/api/v1/resume/parse", {"resume_text": resume_text})

    target_roles: list[str] = parsed.get("target_roles", [])
    skill_obj: dict = parsed.get("skills", {})
    flat_skills: list[str] = (
        skill_obj.get("languages", [])
        + skill_obj.get("frameworks", [])
        + skill_obj.get("databases", [])
        + skill_obj.get("cloud_devops", [])
        + skill_obj.get("tools", [])
        + skill_obj.get("others", [])
    )
    projects_detail: list[dict] = parsed.get("projects", [])
    flat_projects: list[str] = [
        f"{p.get('name', '')} ({', '.join(p.get('technologies', []))})"
        for p in projects_detail
        if p.get("name")
    ]

    values = {
        "desired_role": target_roles[0] if target_roles else "",
        "skills": json.dumps(flat_skills, ensure_ascii=False),
        "certificates": json.dumps(parsed.get("certificates", []), ensure_ascii=False),
        "projects": json.dumps(flat_projects, ensure_ascii=False),
        "target_roles": json.dumps(target_roles, ensure_ascii=False),
        "career_level": parsed.get("career_level", ""),
        "skills_detail": json.dumps(skill_obj, ensure_ascii=False),
        "education": json.dumps(parsed.get("education", []), ensure_ascii=False),
        "experience": json.dumps(parsed.get("experience", []), ensure_ascii=False),
        "projects_detail": json.dumps(projects_detail, ensure_ascii=False),
    }

    return await _upsert_profile(current_user.id, values, db)


@router.post("/me/transcript", response_model=ProfileRead)
async def upload_transcript(
    payload: TranscriptTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    if not payload.transcript_text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="성적표 텍스트가 비어있습니다.")

    parsed = await post_to_ai_service("/api/v1/transcript/parse", {"transcript_text": payload.transcript_text})

    values = {
        "gpa": parsed.get("gpa", ""),
        "gpa_scale": parsed.get("gpa_scale", ""),
        "transcript_strong_subjects": json.dumps(parsed.get("strong_subjects", []), ensure_ascii=False),
        "transcript_weak_subjects": json.dumps(parsed.get("weak_subjects", []), ensure_ascii=False),
        "total_credits": parsed.get("total_credits", ""),
        "completed_semesters": parsed.get("completed_semesters", ""),
    }

    return await _upsert_profile(current_user.id, values, db)


@router.post("/me/portfolio", response_model=ProfileRead)
async def upload_portfolio(
    payload: PortfolioTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    if not payload.portfolio_text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="포트폴리오 텍스트가 비어있습니다.")

    parsed = await post_to_ai_service("/api/v1/portfolio/parse", {"portfolio_text": payload.portfolio_text})

    values = {
        "portfolio_projects": json.dumps(parsed.get("projects", []), ensure_ascii=False),
        "portfolio_total_count": parsed.get("total_project_count", 0),
        "portfolio_solo_count": parsed.get("solo_project_count", 0),
        "portfolio_team_count": parsed.get("team_project_count", 0),
        "portfolio_deployed_count": parsed.get("deployed_project_count", 0),
        "portfolio_total_months": parsed.get("total_duration_months", 0),
    }

    return await _upsert_profile(current_user.id, values, db)


async def _upsert_profile(user_id: int, values: dict, db: Session) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile:
        for key, value in values.items():
            setattr(profile, key, value)
    else:
        profile = Profile(user_id=user_id, **values)
        db.add(profile)
    db.commit()
    db.refresh(profile)
    await _trigger_async_recommendation(user_id, profile)
    return profile

async def _trigger_async_recommendation(user_id: int, profile: Profile):
    payload = {
        "desired_role": profile.desired_role,
        "skills": json.loads(profile.skills) if profile.skills else [],
        "certificates": json.loads(profile.certificates) if profile.certificates else [],
        "projects": json.loads(profile.projects) if profile.projects else []
    }
    
    try:
        await post_to_ai_service("/recommend/match/async", {
            "user_id": user_id,
            "profile": payload
        })
    except Exception as e:
        logger.exception("Failed to trigger async recommendation")


def _extract_text_from_pdf(contents: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)
