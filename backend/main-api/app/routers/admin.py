from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Profile, SavedJob, User, UserRole
from app.schemas import AdminUserRead, UserRoleUpdate

router = APIRouter()


def serialize_user(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/users", response_model=list[AdminUserRead])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserRead]:
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return [serialize_user(user) for user in users]


@router.post("/bootstrap", response_model=AdminUserRead)
def bootstrap_first_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN))
    if admin_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin account already exists",
        )

    current_user.role = UserRole.ADMIN
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserRead:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role",
        )

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.execute(delete(SavedJob).where(SavedJob.user_id == user_id))
    db.execute(delete(Profile).where(Profile.user_id == user_id))
    db.delete(user)
    db.commit()
