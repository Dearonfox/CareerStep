import asyncio
import json
from app.core.config import settings
from app.core.mongo import mongo
from app.core.logging import init_log_db
from app.services.summarizer import JobSummarizer

async def main():
    print("=== 요약 엔진 테스트 시작 ===")
    
    # DB 초기화
    await init_log_db()
    if settings.mongodb_uri:
        print(f"Connecting to MongoDB...")
        await mongo.connect(settings.mongodb_uri)
    else:
        print("MONGODB_URI가 설정되지 않았습니다.")
        return

    # 요약 실행 (20개 제한)
    summarizer = JobSummarizer()
    print("요약 파이프라인 시작 (limit=20)...")
    
    # 건수 먼저 확인
    cursor = mongo.job_raw.find({"status": "detailed"}).limit(20)
    jobs = await cursor.to_list(length=20)
    print(f"대상 공고 건수: {len(jobs)}건")
    
    if not jobs:
        print("요약할 'detailed' 상태의 공고가 없습니다.")
        await mongo.close()
        return

    # 배치 실행
    result = await summarizer.run_batch(limit=20)
    
    print("\n=== 처리 결과 요약 ===")
    print(f"전체 처리: {result.total_processed}건")
    print(f"성공: {result.success_count}건")
    print(f"실패: {result.failed_count}건")
    print(f"무관한 직군(스킵됨): {result.skipped_not_relevant}건")
    
    if result.errors:
        print("\n에러 내역:")
        for err in result.errors:
            print(err)
            
    print("\n=== MongoDB 저장 결과 (첫 번째 성공건) ===")
    doc = await mongo.job_raw.find_one({"status": "summarized"})
    if doc and "summary" in doc:
        print(f"공고 제목: {doc.get('title')}")
        print("요약 결과 (JSON):")
        print(json.dumps(doc["summary"], indent=2, ensure_ascii=False))
        
    await mongo.close()
    print("=== 요약 엔진 테스트 종료 ===")

if __name__ == "__main__":
    asyncio.run(main())
