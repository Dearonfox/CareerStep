from fastapi import APIRouter, Depends
from app.core.security import verify_internal_key
from app.schemas_summarize import SummarizeBatchResult, SummarizeRunRequest, SummarizeStatusResponse
from app.services.summarizer import JobSummarizer
from app.services.router import process_routing_for_job
from app.core.mongo import mongo

router = APIRouter(dependencies=[Depends(verify_internal_key)])

@router.post("/run", response_model=SummarizeBatchResult)
async def run_summarize(request: SummarizeRunRequest):
    """배치 요약을 실행합니다."""
    if request.dry_run:
        # Dry run: 대상 공고 목록 및 건수만 반환
        batch_size = request.limit or 10
        cursor = mongo.job_raw.find({"status": "detailed"}).limit(batch_size)
        jobs = await cursor.to_list(length=batch_size)
        return SummarizeBatchResult(total_processed=len(jobs))

    summarizer = JobSummarizer()
    return await summarizer.run_batch(limit=request.limit)

@router.get("/status", response_model=SummarizeStatusResponse)
async def get_status():
    """현재 요약 파이프라인 진행 상태를 반환합니다."""
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    cursor = mongo.job_raw.aggregate(pipeline)
    counts = await cursor.to_list(length=None)
    
    status_map = {doc["_id"]: doc["count"] for doc in counts}
    
    total = sum(status_map.values())
    detailed = status_map.get("detailed", 0)
    summarized = status_map.get("summarized", 0)
    failed = status_map.get("summary_failed", 0)
    
    # relevant 필터링은 summary 필드 안에 있으므로 따로 세야 하지만 임시로 0
    not_relevant = 0

    return SummarizeStatusResponse(
        total_jobs=total,
        detailed=detailed,
        summarized=summarized,
        failed=failed,
        not_relevant=not_relevant
    )

@router.post("/route", response_model=SummarizeBatchResult)
async def run_routing(request: SummarizeRunRequest):
    """
    status가 'summarized'인 공고들을 대상으로 라우팅(scoring)을 수행합니다.
    (LLM 호출 없이 로컬 키워드 매칭 수행, 멱등성 보장)
    """
    batch_size = request.limit or 100
    
    if request.dry_run:
        cursor = mongo.job_raw.find({"status": "summarized"}).limit(batch_size)
        jobs = await cursor.to_list(length=batch_size)
        return SummarizeBatchResult(total_processed=len(jobs))
        
    cursor = mongo.job_raw.find({"status": "summarized"}).limit(batch_size)
    jobs = await cursor.to_list(length=batch_size)
    
    if not jobs:
        return SummarizeBatchResult(total_processed=0)
        
    success_count = 0
    failed_count = 0
    errors = []
    
    for job in jobs:
        try:
            routed_job = process_routing_for_job(job)
            
            # MongoDB 업데이트
            await mongo.job_raw.update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "summary": routed_job["summary"],
                    "status": "routed"
                }}
            )
            success_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({"error": str(e), "job_id": job.get("_id")})
            
    return SummarizeBatchResult(
        total_processed=len(jobs),
        success_count=success_count,
        failed_count=failed_count,
        errors=errors
    )
