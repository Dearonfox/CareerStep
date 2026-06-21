from fastapi import APIRouter, Depends
from app.core.security import verify_internal_key
from app.schemas_summarize import SummarizeBatchResult, SummarizeRunRequest, SummarizeStatusResponse
from app.services.activity_summarizer import ActivitySummarizer
from app.core.mongo import mongo

router = APIRouter(dependencies=[Depends(verify_internal_key)])

@router.post("/run", response_model=SummarizeBatchResult)
async def run_summarize(request: SummarizeRunRequest):
    """대외활동 게시글 배치 요약을 실행합니다."""
    if request.dry_run:
        batch_size = request.limit or 10
        cursor = mongo.activities.find({"status": "detailed"}).limit(batch_size)
        articles = await cursor.to_list(length=batch_size)
        return SummarizeBatchResult(total_processed=len(articles))

    summarizer = ActivitySummarizer()
    return await summarizer.run_batch(limit=request.limit)

@router.get("/status", response_model=SummarizeStatusResponse)
async def get_status():
    """현재 대외활동 요약 파이프라인 진행 상태를 반환합니다."""
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    cursor = mongo.activities.aggregate(pipeline)
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
