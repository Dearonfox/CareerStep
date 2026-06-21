from fastapi import APIRouter, Depends
import json
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AIRecommendRequest, EssayDraftRequest
from app.services.ai_client import post_to_ai_service

router = APIRouter()


@router.post("/recommend/jobs")
async def recommend_jobs(
    payload: AIRecommendRequest,
    _: User = Depends(get_current_user),
) -> dict:
    return await post_to_ai_service("/recommend/jobs", payload.model_dump())


@router.post("/essay/draft")
async def draft_essay(
    payload: EssayDraftRequest,
    _: User = Depends(get_current_user),
) -> dict:
    return await post_to_ai_service("/essay/draft", payload.model_dump())


@router.get("/recommendations/me")
async def get_my_recommendations(
    current_user: User = Depends(get_current_user)
) -> dict:
    from app.services.ai_client import get_from_ai_service
    # ai-api에 GET /match/me?user_id=... 로 요청 프록시
    return await get_from_ai_service("/recommend/match/me", params={"user_id": current_user.id})
