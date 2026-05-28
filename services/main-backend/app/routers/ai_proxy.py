from fastapi import APIRouter, Depends

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
