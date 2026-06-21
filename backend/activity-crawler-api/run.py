import os
import sys
import json
import time
from datetime import datetime
from collections import Counter

# Windows 콘솔 기본 인코딩(cp949)이 일부 유니코드 문자(en dash 등)를 출력하지 못해
# print()가 예외를 던지는 문제를 방지하기 위해 stdout을 UTF-8로 강제 고정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import BOARDS, MAX_PAGES, CRAWL_DELAY, OUTPUT_FILE, DATA_DIR, MONGODB_URI
from crawler import categorize, fetch_article_detail, fetch_board_articles


def run_pipeline(max_pages: int | None = MAX_PAGES):
    print("=" * 70)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 전북대 CSAI 대외활동 수집 파이프라인 시작")
    if max_pages:
        print(f"설정: 게시판당 최근 {max_pages}페이지")
    print("=" * 70)

    os.makedirs(DATA_DIR, exist_ok=True)

    all_articles = []
    total_boards = len(BOARDS)

    for idx, (name, code) in enumerate(BOARDS.items(), 1):
        print(f"[{idx}/{total_boards}] '{name}' (코드: {code}) 수집 중...")
        articles = fetch_board_articles(name, code, max_pages=max_pages, delay=CRAWL_DELAY)
        print(f"  -> {len(articles)}건 수집 완료")
        all_articles.extend(articles)

    print("\n" + "=" * 70)
    print(f"전체 수집 완료! 총 {len(all_articles)}건 수집됨")

    # 중복 제거 (board_code + article_id 기준)
    seen = set()
    unique_articles = []
    for article in all_articles:
        key = f"{article['board_code']}_{article['article_id']}"
        if key not in seen:
            seen.add(key)
            unique_articles.append(article)

    print(f"중복 제거 후 고유 게시글 수: {len(unique_articles)}건")

    # 카테고리별 통계 출력 (제목 기준 1차 분류)
    cat_counts = Counter(categorize(a["title"]) for a in unique_articles)
    print("\n[카테고리별 분포]")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt}건")

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_articles, f, ensure_ascii=False, indent=2)
        print(f"\n성공적으로 로컬 파일에 데이터를 저장했습니다: {OUTPUT_FILE}")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

    # MongoDB Atlas 적재 및 상세 수집 연동
    if MONGODB_URI:
        print("\n>>> MongoDB Atlas 클라우드 데이터 적재 시작...")
        try:
            from db import MongoDBClient
            db_client = MongoDBClient()
            db_client.upsert_activities(unique_articles)

            # --- 2단계: 상세 페이지 마크다운/이미지 수집 & 업데이트 ---
            print("\n>>> 2단계: 게시글 상세 본문 마크다운 변환 및 업데이트 시작...")
            total_articles = len(unique_articles)
            for s_idx, article in enumerate(unique_articles, 1):
                board_code = article["board_code"]
                article_id = article["article_id"]

                print(f"  [{s_idx}/{total_articles}] '{article['title'][:30]}' (ID: {article_id}) 상세 수집 중...")

                detail_data = fetch_article_detail(article)
                detail_data["category"] = categorize(article["title"])

                if detail_data.get("error_message"):
                    print(f"    [경고] 상세 수집 실패: {detail_data['error_message']}")
                elif detail_data.get("is_image_job"):
                    print(f"    [이미지] 이미지 전용 게시글 감지 (이미지 수: {len(detail_data['image_urls'])}개)")
                else:
                    print(f"    [텍스트] 마크다운 변환 성공 (텍스트 크기: {len(detail_data['detail_markdown']):,} 자)")

                db_client.update_activity_detail(board_code, article_id, detail_data)

                if s_idx < total_articles:
                    time.sleep(CRAWL_DELAY * 0.3)

            db_client.close()
        except Exception as e:
            print(f"[오류] MongoDB Atlas 적재 중 예외 발생: {e}")
    else:
        print("\n>>> MONGODB_URI 환경변수가 없어 클라우드 적재 단계를 건너뜁니다.")

    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="전북대 CSAI 대외활동 수집")
    parser.add_argument("--pages", type=int, default=None, help="게시판당 최대 페이지 수 (기본: 전체)")
    args = parser.parse_args()
    run_pipeline(max_pages=args.pages)
