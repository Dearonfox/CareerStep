"""
MongoDB(job_raw) → MySQL(jobs) 동기화 스크립트

실행 방법:
    python sync_to_mysql.py

동작:
    1. MongoDB에서 status = "detailed" 인 공고만 조회
    2. 필드 변환 후 MySQL jobs 테이블에 upsert
    3. 동기화 완료된 MongoDB 도큐먼트에 synced_to_mysql = true 마킹
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from sqlalchemy import create_engine, text

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MYSQL_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://careerstep:careerstep_password@localhost:3306/careerstep",
)

BATCH_SIZE = 100  # 한 번에 처리할 공고 수


# ── 텍스트 길이 제한 (MySQL TEXT 컬럼 초과 방지) ──────────────────────
MAX_DESCRIPTION_LEN = 60_000


def _truncate(text: str, limit: int = MAX_DESCRIPTION_LEN) -> str:
    return text[:limit] if text and len(text) > limit else (text or "")


# ── 필드 변환: MongoDB 도큐먼트 → MySQL jobs 행 ───────────────────────
def _to_mysql_row(doc: dict) -> dict | None:
    title = doc.get("title", "").strip()
    company = doc.get("company_name", "").strip()
    if not title or not company:
        return None

    meta: dict = doc.get("meta", {})
    location = meta.get("location", "N/A")
    employment_type = meta.get("employment_type", "N/A")

    tags: list[str] = doc.get("tags", [])
    skills_json = json.dumps(tags, ensure_ascii=False)

    description = _truncate(doc.get("detail_markdown", "") or "")

    return {
        "mongo_id": str(doc.get("_id", "")),
        "title": title[:200],
        "company": company[:150],
        "location": location[:150],
        "employment_type": employment_type[:80],
        "skills": skills_json,
        "description": description,
    }


# ── MySQL upsert (mongo_id 기준 중복 방지) ────────────────────────────
UPSERT_SQL = text("""
    INSERT INTO jobs (mongo_id, title, company, location, employment_type, skills, description)
    VALUES (:mongo_id, :title, :company, :location, :employment_type, :skills, :description)
    ON DUPLICATE KEY UPDATE
        title            = VALUES(title),
        company          = VALUES(company),
        location         = VALUES(location),
        employment_type  = VALUES(employment_type),
        skills           = VALUES(skills),
        description      = VALUES(description)
""")


def _ensure_mongo_id_column(engine) -> None:
    """jobs 테이블에 mongo_id 컬럼이 없으면 추가."""
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() "
            "AND table_name = 'jobs' "
            "AND column_name = 'mongo_id'"
        ))
        exists = result.scalar() > 0
        if not exists:
            conn.execute(text(
                "ALTER TABLE jobs "
                "ADD COLUMN mongo_id VARCHAR(40) NULL UNIQUE"
            ))
            conn.commit()
            print("[DB] jobs 테이블에 mongo_id 컬럼 추가 완료")


# ── 메인 동기화 파이프라인 ────────────────────────────────────────────
def run_sync() -> None:
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] MongoDB → MySQL 동기화 시작")
    print("=" * 60)

    if not MONGODB_URI:
        print("[오류] MONGODB_URI 환경변수가 없습니다.")
        sys.exit(1)

    # MongoDB 연결
    mongo_client = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
    collection = mongo_client["careerstep"]["job_raw"]
    mongo_client.admin.command("ping")
    print("[연결] MongoDB Atlas 연결 성공")

    # MySQL 연결
    engine = create_engine(MYSQL_URL, pool_pre_ping=True)
    _ensure_mongo_id_column(engine)
    print("[연결] MySQL 연결 성공")

    # status = "detailed" 이고 아직 동기화 안 된 공고만 조회
    query = {
        "status": "detailed",
        "is_image_job": {"$ne": True},
        "$or": [
            {"synced_to_mysql": {"$exists": False}},
            {"synced_to_mysql": False},
        ],
    }
    total = collection.count_documents(query)
    print(f"[정보] 동기화 대상 공고: {total}개")

    if total == 0:
        print("[완료] 새로 동기화할 공고가 없습니다.")
        mongo_client.close()
        return

    synced = 0
    failed = 0
    skip = 0

    cursor = collection.find(query).batch_size(BATCH_SIZE)

    with engine.connect() as conn:
        for doc in cursor:
            row = _to_mysql_row(doc)
            if row is None:
                skip += 1
                continue

            try:
                conn.execute(UPSERT_SQL, row)
                # MongoDB에 동기화 완료 마킹
                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"synced_to_mysql": True, "synced_at": datetime.now().isoformat()}},
                )
                synced += 1
            except Exception as e:
                print(f"  [오류] {doc.get('title', '?')} ({doc.get('_id')}) 실패: {e}")
                failed += 1

        conn.commit()

    mongo_client.close()

    print("=" * 60)
    print(f"동기화 완료 — 성공: {synced}개 | 실패: {failed}개 | 건너뜀: {skip}개")
    print("=" * 60)


if __name__ == "__main__":
    run_sync()
