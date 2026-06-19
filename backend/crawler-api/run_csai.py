"""
전북대 컴퓨터인공지능학부 대외활동 수집 파이프라인

실행 방법:
    python run_csai.py              # 전체 수집
    python run_csai.py --pages 5   # 게시판당 최근 5페이지만
"""

import argparse
import json
import os
from collections import Counter
from datetime import datetime

from config import DATA_DIR, MONGODB_URI
from csai_crawler import BOARDS, crawl_board
from db import MongoDBClient

OUTPUT_FILE = os.path.join(DATA_DIR, "csai_activities.json")
CRAWL_DELAY = 1.0


def run_pipeline(max_pages: int | None = None) -> None:
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 전북대 CSAI 대외활동 수집 시작")
    if max_pages:
        print(f"설정: 게시판당 최근 {max_pages}페이지")
    print("=" * 60)

    os.makedirs(DATA_DIR, exist_ok=True)

    all_activities: list[dict] = []

    for board_name, board_code in BOARDS.items():
        print(f"\n[게시판] {board_name} (코드: {board_code})")
        articles = crawl_board(board_name, board_code, max_pages=max_pages, delay=CRAWL_DELAY)
        print(f"  → {len(articles)}건 수집 완료")
        all_activities.extend(articles)

    # 중복 제거 (board_code + article_id 기준)
    seen = set()
    unique = []
    for a in all_activities:
        key = f"{a['board_code']}_{a['article_id']}"
        if key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"\n총 {len(unique)}건 (중복 제거 후)")

    # 카테고리별 통계 출력
    cat_counts = Counter(a["category"] for a in unique)
    print("\n[카테고리별 분포]")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt}건")

    # 로컬 JSON 저장
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
        print(f"\n로컬 저장 완료: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[오류] 로컬 저장 실패: {e}")

    # MongoDB 저장 (MongoDBClient 재사용)
    if MONGODB_URI:
        print("\n>>> MongoDB Atlas 저장 시작...")
        db_client = MongoDBClient()
        db_client.upsert_activities(unique)
        db_client.close()
    else:
        print("\n>>> MONGODB_URI 없음 — 로컬 JSON만 저장됨")

    print("\n" + "=" * 60)
    print("파이프라인 완료")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="전북대 CSAI 대외활동 수집")
    parser.add_argument("--pages", type=int, default=None, help="게시판당 최대 페이지 수 (기본: 전체)")
    args = parser.parse_args()
    run_pipeline(max_pages=args.pages)
