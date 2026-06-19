from fastapi import APIRouter, Depends

from app.core.security import verify_internal_key
from app.schemas import RecommendJobsRequest, RecommendJobsResponse
from app.gateway import gpt_gateway
from app.services.prompts import RECOMMEND_JOBS_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/jobs", response_model=RecommendJobsResponse)
async def recommend_jobs(payload: RecommendJobsRequest) -> RecommendJobsResponse:
    result = await gpt_gateway.chat_json(
        system_prompt=RECOMMEND_JOBS_SYSTEM_PROMPT,
        payload=payload.model_dump(),
        endpoint="/recommend/jobs",
    )
    return RecommendJobsResponse.model_validate(result)
