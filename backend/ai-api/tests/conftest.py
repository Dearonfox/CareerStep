import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# 테스트 시작 전 환경 변수 주입 (모듈 import보다 먼저 실행)
os.environ["OPENAI_API_KEY"] = "sk-test-key-not-real"
os.environ["INTERNAL_SERVICE_KEY"] = "test-internal-key"


@pytest.fixture
def tmp_db_path(tmp_path):
    """테스트마다 격리된 임시 SQLite DB 경로를 제공합니다."""
    db_path = str(tmp_path / "test_ai_logs.sqlite3")
    return db_path


@pytest.fixture
def patch_settings(tmp_db_path, monkeypatch):
    """settings 객체의 값을 테스트용으로 패치합니다."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ai_log_db_path", tmp_db_path)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-key-not-real")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "max_tokens", 1500)
    monkeypatch.setattr(settings, "openai_max_retries", 3)
    monkeypatch.setattr(settings, "openai_rpm_limit", 10)
    monkeypatch.setattr(settings, "openai_tpm_limit", 5000)
    monkeypatch.setattr(settings, "openai_concurrency_limit", 2)
    return settings


@pytest.fixture
def gateway(patch_settings):
    """테스트마다 격리된 새 GPTGateway 인스턴스를 생성합니다.
    싱글톤이 아닌 fresh instance로 Semaphore/rate_limiter 상태가 공유되지 않습니다.
    """
    from app.gateway.client import GPTGateway

    gw = GPTGateway()
    return gw


def _make_mock_response(content: str = '{"status": "ok"}', prompt_tokens: int = 100, completion_tokens: int = 50):
    """OpenAI API 성공 응답 Mock 객체를 생성하는 헬퍼입니다."""
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens

    mock_choice = MagicMock()
    mock_choice.message.content = content

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    return mock_response


@pytest.fixture
def mock_success_response():
    """정상 응답을 반환하는 Mock을 제공합니다."""
    return _make_mock_response()


@pytest.fixture
def mock_openai_success(gateway, mock_success_response):
    """Gateway의 OpenAI 클라이언트를 성공 응답 Mock으로 교체합니다."""
    mock_create = AsyncMock(return_value=mock_success_response)
    gateway.client.chat.completions.create = mock_create
    return mock_create
