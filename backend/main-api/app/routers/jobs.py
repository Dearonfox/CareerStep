import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

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


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobRead]:
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
