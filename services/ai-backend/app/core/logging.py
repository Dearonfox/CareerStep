import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


def init_log_db() -> None:
    Path(settings.ai_log_db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.ai_log_db_path) as conn:
        conn.execute(
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


def write_ai_log(endpoint: str, request_data: dict[str, Any], response_data: dict[str, Any]) -> None:
    init_log_db()
    violation_detected = int(bool(response_data.get("policy_violation")))
    with sqlite3.connect(settings.ai_log_db_path) as conn:
        conn.execute(
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
