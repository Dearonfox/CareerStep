import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import Profile, User
from app.schemas import ProfileRead, ProfileUpsert

router = APIRouter()


@router.get("/me", response_model=ProfileRead | None)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile | None:
    return db.scalar(select(Profile).where(Profile.user_id == current_user.id))


@router.put("/me", response_model=ProfileRead)
def upsert_my_profile(
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
    return profile
