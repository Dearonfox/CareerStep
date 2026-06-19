from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import delete_refresh_token, store_refresh_token
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models import User
from app.schemas import TokenPair, UserCreate, UserLogin

router = APIRouter()


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=payload.email, name=payload.name, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token()
    store_refresh_token(refresh_token, user.id, 60 * 60 * 24 * 14)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token()
    store_refresh_token(refresh_token, user.id, 60 * 60 * 24 * 14)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/logout")
def logout(refresh_token: str) -> dict[str, str]:
    delete_refresh_token(refresh_token)
    return {"message": "logged out"}
