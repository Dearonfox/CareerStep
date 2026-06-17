import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import User, UserPreference
from app.schemas import UserPreferenceRead, UserPreferenceUpsert

router = APIRouter()


@router.get("/me", response_model=UserPreferenceRead | None)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreference | None:
    return db.scalar(select(UserPreference).where(UserPreference.user_id == current_user.id))


@router.put("/me", response_model=UserPreferenceRead)
def upsert_my_preferences(
    payload: UserPreferenceUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreference:
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == current_user.id))
    values = {
        "job_roles": json.dumps(payload.job_roles, ensure_ascii=False),
        "company_types": json.dumps(payload.company_types, ensure_ascii=False),
        "preferred_regions": json.dumps(payload.preferred_regions, ensure_ascii=False),
        "target_timeline": payload.target_timeline,
        "weekly_hours": payload.weekly_hours,
        "wants_cert_upgrade": payload.wants_cert_upgrade,
        "priority_area": payload.priority_area,
    }
    if pref:
        for key, value in values.items():
            setattr(pref, key, value)
    else:
        pref = UserPreference(user_id=current_user.id, **values)
        db.add(pref)
    db.commit()
    db.refresh(pref)
    return pref
