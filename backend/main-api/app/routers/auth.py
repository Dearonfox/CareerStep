from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import delete_refresh_token, get_refresh_token_user_id, store_refresh_token
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models import User
from app.schemas import RefreshTokenRequest, TokenPair, UserCreate, UserLogin

REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14

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
    store_refresh_token(refresh_token, user.id, REFRESH_TOKEN_TTL_SECONDS)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token()
    store_refresh_token(refresh_token, user.id, REFRESH_TOKEN_TTL_SECONDS)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenPair:
    user_id = get_refresh_token_user_id(payload.refresh_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 리프레시 토큰 회전: 기존 토큰 폐기 후 새 토큰 발급 (탈취 시 재사용 방지)
    delete_refresh_token(payload.refresh_token)
    access_token = create_access_token(str(user.id), user.role.value)
    new_refresh_token = create_refresh_token()
    store_refresh_token(new_refresh_token, user.id, REFRESH_TOKEN_TTL_SECONDS)
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token, user=user)


@router.post("/logout")
def logout(refresh_token: str) -> dict[str, str]:
    delete_refresh_token(refresh_token)
    return {"message": "logged out"}
