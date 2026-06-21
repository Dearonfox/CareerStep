from fastapi import APIRouter, Depends, BackgroundTasks
import httpx
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

from app.core.security import verify_internal_key
from app.core.config import settings
from app.core.mongo import mongo
from app.schemas import RecommendJobsRequest, RecommendJobsResponse, ProfileInput, MatchAsyncRequest
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


async def process_background_match(user_id: int, profile: ProfileInput):
    from datetime import datetime
    try:
        logger.info(f"Starting background match job for user_id: {user_id}")
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
                
        response = await match_jobs(
            profile=profile.model_dump(),
            positions=positions,
            demand=demand,
            model=settings.openai_model
        )
        
        logger.info(f"Match completed for user_id: {user_id}. Saving to MongoDB.")
        await mongo.recommendation_cache.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": "done",
                "data": response.model_dump(),
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
    except Exception as e:
        logger.exception("Error in background match job")
        try:
            await mongo.recommendation_cache.update_one(
                {"user_id": user_id},
                {"$set": {
                    "status": "error",
                    "message": str(e),
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as inner_e:
            logger.exception("Failed to update MongoDB error state")


@router.get("/test_db")
def test_db():
    return {"db_is_none": mongo.db is None}

@router.post("/match/async", status_code=202)
async def recommend_match_async(payload: MatchAsyncRequest, background_tasks: BackgroundTasks):
    from datetime import datetime
    """
    비동기 원스톱 추천 API.
    작업은 백그라운드에서 실행되며 결과는 MongoDB에 저장됩니다.
    """
    await mongo.recommendation_cache.update_one(
        {"user_id": payload.user_id},
        {"$set": {
            "status": "pending",
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    background_tasks.add_task(process_background_match, payload.user_id, payload.profile)
    return {"status": "processing"}

@router.get("/match/me")
async def get_my_match(user_id: int):
    """
    내부 통신용: 사용자 ID로 추천 상태 및 결과를 조회합니다.
    """
    doc = await mongo.recommendation_cache.find_one({"user_id": user_id})
    if not doc:
        return {"status": "no_data", "message": "프로필을 저장하면 추천이 생성됩니다."}
    
    status = doc.get("status", "pending")
    if status == "pending":
        return {"status": "pending", "message": "추천 결과를 생성 중입니다."}
    if status == "error":
        return {"status": "error", "message": doc.get("message", "추천 생성 중 오류가 발생했습니다.")}
    
    return {"status": "done", "data": doc.get("data", {})}
