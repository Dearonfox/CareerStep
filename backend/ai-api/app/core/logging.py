import json
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


async def init_log_db() -> None:
    Path(settings.ai_log_db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.ai_log_db_path) as db:
        # ai_logs 테이블 생성 (기존 포맷 유지)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                violation_detected INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        # ai_usage 테이블 생성 (토큰 소모 및 비용 분석용)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                status TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def write_ai_log(endpoint: str, request_data: dict[str, Any], response_data: dict[str, Any]) -> None:
    await init_log_db()
    violation_detected = int(bool(response_data.get("policy_violation")))
    async with aiosqlite.connect(settings.ai_log_db_path) as db:
        await db.execute(
            """
            INSERT INTO ai_logs (endpoint, request_json, response_json, violation_detected, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                json.dumps(request_data, ensure_ascii=False),
                json.dumps(response_data, ensure_ascii=False),
                violation_detected,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()


async def write_ai_usage(
    endpoint: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    status: str,
    retry_count: int,
    latency_ms: int,
) -> None:
    await init_log_db()
    async with aiosqlite.connect(settings.ai_log_db_path) as db:
        await db.execute(
            """
            INSERT INTO ai_usage (
                endpoint, model, prompt_tokens, completion_tokens, total_tokens, 
                estimated_cost, status, retry_count, latency_ms, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost,
                status,
                retry_count,
                latency_ms,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
