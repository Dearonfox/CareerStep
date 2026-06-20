import os
import json
import time
from datetime import datetime
from config import DUTY_MAP, PAGE_SIZE, CRAWL_DELAY, OUTPUT_FILE, DATA_DIR, MONGODB_URI
from crawler import fetch_category_jobs, fetch_job_detail

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
        
    # MongoDB Atlas 적재 및 상세 수집 연동
    if MONGODB_URI:
        print("\n>>> MongoDB Atlas 클라우드 데이터 적재 시작...")
        try:
            from db import MongoDBClient
            db_client = MongoDBClient()
            db_client.upsert_jobs(unique_jobs)
            
            # --- 2단계: 상세 페이지 마크다운 수집 & 업데이트 ---
            print("\n>>> 2단계: 채용 상세 요강 마크다운 변환 및 업데이트 시작...")
            total_jobs = len(unique_jobs)
            
            try:
                for s_idx, job in enumerate(unique_jobs, 1):
                    job_id = job["job_id"]
                    company = job["company_name"]
                    
                    print(f"  [{s_idx}/{total_jobs}] '{company}' (ID: {job_id}) 상세 요강 수집 중...")
                    
                    # 상세 페이지 수집 및 마크다운 정제 (이미지 및 에러 케이스 자동 대응)
                    detail_data = fetch_job_detail(job_id)
                    
                    if detail_data.get("error_message"):
                        print(f"    [경고] 상세 수집 실패: {detail_data['error_message']}")
                    elif detail_data.get("is_image_job"):
                        print(f"    [이미지] 이미지 전용 공고 감지 (이미지 수: {len(detail_data['image_urls'])}개)")
                    else:
                        print(f"    [텍스트] 마크다운 변환 성공 (텍스트 크기: {len(detail_data['detail_markdown']):,} 자)")
                    
                    # MongoDB에 개별 도큐먼트 업데이트
                    db_client.update_job_detail(job_id, detail_data)
                    
                    # 봇 탐지 방지 지연
                    if s_idx < total_jobs:
                        time.sleep(CRAWL_DELAY)
            except (KeyboardInterrupt, Exception) as e:
                print(f"\n[오류/중단] 수집이 강제 중단되었습니다. 사유: {e}")
                raise
            finally:
                deleted_count = db_client.delete_pending_jobs()
                if deleted_count > 0:
                    print(f"\n[롤백] 중단으로 인해 상세 조회가 안 된 pending 데이터 {deleted_count}건을 깔끔하게 삭제(롤백)했습니다.")
                db_client.close()
                
        except Exception as e:
            print(f"[오류] MongoDB Atlas 적재 중 예외 발생: {e}")
    else:
        print("\n>>> MONGODB_URI 환경변수가 없어 클라우드 적재 단계를 건너뜁니다.")

    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
