from fastapi import APIRouter, Depends

from app.core.logging import write_ai_log
from app.core.security import verify_internal_key
from app.schemas import RecommendJobsRequest, RecommendJobsResponse
from app.services.openai_client import request_json
from app.services.prompts import RECOMMEND_JOBS_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/jobs", response_model=RecommendJobsResponse)
def recommend_jobs(payload: RecommendJobsRequest) -> RecommendJobsResponse:
    result = request_json(RECOMMEND_JOBS_SYSTEM_PROMPT, payload.model_dump())
    response = RecommendJobsResponse.model_validate(result)
    write_ai_log("/recommend/jobs", payload.model_dump(), response.model_dump())
    return response
