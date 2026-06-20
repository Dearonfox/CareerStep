from fastapi import APIRouter, Depends
from typing import Dict, Any, List

from app.core.security import verify_internal_key
from app.core.config import settings
from app.core.mongo import mongo
from app.schemas import RecommendJobsRequest, RecommendJobsResponse, ProfileInput
from app.gateway import gpt_gateway
from app.services.prompts import MATCH_JOBS_SYSTEM_PROMPT
from app.services.demand_aggregator import aggregate_demand
from app.services.matcher import match_jobs

router = APIRouter(dependencies=[Depends(verify_internal_key)])


@router.post("/jobs", response_model=RecommendJobsResponse)
async def recommend_jobs(payload: RecommendJobsRequest) -> RecommendJobsResponse:
    """
    내부 전용 API (main-api 호출용).
    직접 후보 리스트를 받아서 LLM 배치 채점을 수행합니다.
    """
    # Phase 2에서 로드맵 모델 분리 가능
    result = await gpt_gateway.chat_json(
        system_prompt=MATCH_JOBS_SYSTEM_PROMPT,
        payload=payload.model_dump(),
        endpoint="/recommend/jobs",
        response_format=RecommendJobsResponse,
        model=settings.openai_model
    )
    return RecommendJobsResponse.model_validate(result)


@router.post("/match", response_model=RecommendJobsResponse)
async def recommend_match(profile: ProfileInput) -> RecommendJobsResponse:
    """
    원스톱 추천 API. DB에서 직접 읽어 retrieve -> batch 채점까지 수행.
    """
    cursor = mongo.job_raw.find({"status": "routed"})
    jobs = await cursor.to_list(length=None)
    
    demand = aggregate_demand(jobs)
    
    positions = []
    for job in jobs:
        summary = job.get("summary", {})
        rels = summary.get("relevant_positions", [])
        for p in rels:
            pos_dict = dict(p)
            pos_dict["job_id"] = str(job.get("job_id", ""))
            pos_dict["company_name"] = job.get("company_name", "")
            positions.append(pos_dict)
            
    # Phase 2에서 로드맵 모델 분리 가능
    response = await match_jobs(
        profile=profile.model_dump(),
        positions=positions,
        demand=demand,
        model=settings.openai_model
    )
    
    return response
