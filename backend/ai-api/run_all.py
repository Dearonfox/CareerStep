import asyncio
from app.core.config import settings
from app.core.mongo import mongo
from app.core.logging import init_log_db
from app.services.summarizer import JobSummarizer

async def main():
    print("=== 전체 공고 요약 자동화 스크립트 시작 ===")
    
    await init_log_db()
    await mongo.connect(settings.mongodb_uri)
    
    summarizer = JobSummarizer()
    batch_size = 20
    total_processed = 0
    total_success = 0
    total_failed = 0
    
    while True:
        # 남은 'detailed' 공고 개수 확인
        remaining = await mongo.job_raw.count_documents({"status": "detailed"})
        if remaining == 0:
            print("\n요약할 공고가 더 이상 없습니다! 모두 완료되었습니다.")
            break
            
        print(f"\n[진행 상황] 남은 공고: {remaining}건 -> {batch_size}건 배치 처리 시작...")
        
        # 20건씩 가져와서 처리
        result = await summarizer.run_batch(limit=batch_size)
        
        total_processed += result.total_processed
        total_success += result.success_count
        total_failed += result.failed_count
        
        print(f"방금 배치 결과: 성공 {result.success_count}건, 실패 {result.failed_count}건, 무관 {result.skipped_not_relevant}건")
        
        # 만약 에러가 발생했다면 일부 출력
        if result.errors:
            print("발생한 에러 일부:")
            for err in result.errors[:3]:
                print(f" - {err}")
                
        # 배치를 돌렸는데도 처리된 건수가 0이면 (무한 루프 방지)
        if result.total_processed == 0:
            print("가져온 공고가 없거나 처리되지 않아 중단합니다.")
            break

    print("\n=== 최종 처리 결과 요약 ===")
    print(f"총 처리 시도: {total_processed}건")
    print(f"총 성공: {total_success}건")
    print(f"총 실패: {total_failed}건")
    
    await mongo.close()
    print("=== 스크립트 종료 ===")

if __name__ == "__main__":
    asyncio.run(main())
