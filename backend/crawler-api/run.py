import os
import json
import time
from datetime import datetime
from config import DUTY_MAP, PAGE_SIZE, CRAWL_DELAY, OUTPUT_FILE, DATA_DIR, MONGODB_URI
from crawler import fetch_category_jobs

def run_pipeline():
    print("=" * 70)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 잡코리아 채용 정보 수집 파이프라인 시작")
    print(f"설정: 카테고리당 상위 {PAGE_SIZE}개 수집")
    print("=" * 70)

    # 데이터 저장 디렉토리 보장
    os.makedirs(DATA_DIR, exist_ok=True)

    all_jobs = []
    total_categories = len(DUTY_MAP)

    for idx, (name, code) in enumerate(DUTY_MAP.items(), 1):
        print(f"[{idx}/{total_categories}] '{name}' (코드: {code}) 수집 중...")
        
        # 실제 크롤링 실행
        jobs = fetch_category_jobs(name, code, target_count=PAGE_SIZE)
        
        print(f"  -> {len(jobs)}개 공고 수집 완료")
        all_jobs.extend(jobs)

        # 봇 탐지 방지 지연
        if idx < total_categories:
            time.sleep(CRAWL_DELAY)

    # 결과 파일 저장
    print("\n" + "=" * 70)
    print(f"전체 수집 완료! 총 {len(all_jobs)}개 수집됨")
    
    # 중복 제거 (여러 카테고리에 중복 노출된 동일 공고 ID 기준)
    seen_ids = set()
    unique_jobs = []
    for job in all_jobs:
        jid = job["job_id"]
        if jid not in seen_ids:
            seen_ids.add(jid)
            unique_jobs.append(job)
            
    print(f"중복 제거 후 고유 공고 수: {len(unique_jobs)}개")

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_jobs, f, ensure_ascii=False, indent=2)
        print(f"성공적으로 로컬 파일에 데이터를 저장했습니다: {OUTPUT_FILE}")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        
    # MongoDB Atlas 적재 연동
    if MONGODB_URI:
        print("\n>>> MongoDB Atlas 클라우드 데이터 적재 시작...")
        try:
            from db import MongoDBClient
            db_client = MongoDBClient()
            db_client.upsert_jobs(unique_jobs)
            db_client.close()
        except Exception as e:
            print(f"❌ MongoDB Atlas 적재 중 예외 발생: {e}")
    else:
        print("\n>>> MONGODB_URI 환경변수가 없어 클라우드 적재 단계를 건너뜁니다.")
        
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
