"""
에러 폴백 및 재시도 로직 테스트 (retry 범주)

smoke: 429 RateLimitError 재시도 성공 시나리오
full:  5xx 재시도, 클라이언트 에러 즉시 실패, JSON 깨짐 재시도, 최대 재시도 초과
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import openai

from tests.conftest import _make_mock_response


# ──────────────────────────────────────────────
# [SMOKE] 429 RateLimitError → Backoff → 재시도 성공
# ──────────────────────────────────────────────
@pytest.mark.smoke
@pytest.mark.retry
async def test_retry_on_rate_limit(gateway, patch_settings):
    """429 에러가 발생하면 Exponential Backoff 후 재시도하여 정상 응답을 반환해야 합니다."""
    success_response = _make_mock_response()
    call_count = 0

    async def mock_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            )
        return success_response

    gateway.client.chat.completions.create = AsyncMock(side_effect=mock_effect)

    # max_retries를 1로 줄여서 테스트 시간 단축
    patch_settings.openai_max_retries = 1

    result = await gateway.chat_json("System", {"test": "retry"}, "/test/retry")

    assert result == {"status": "ok"}
    assert call_count == 2, f"Expected 2 API calls (1 fail + 1 success), got {call_count}"


# ──────────────────────────────────────────────
# [FULL] 500/502 서버 에러 → 재시도 성공
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.retry
async def test_retry_on_server_error(gateway, patch_settings):
    """InternalServerError(500) 발생 시 재시도하여 성공해야 합니다."""
    success_response = _make_mock_response()
    call_count = 0

    async def mock_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.InternalServerError(
                "Internal server error",
                response=MagicMock(status_code=500),
                body=None,
            )
        return success_response

    gateway.client.chat.completions.create = AsyncMock(side_effect=mock_effect)
    patch_settings.openai_max_retries = 1

    result = await gateway.chat_json("System", {"test": "500"}, "/test/500")

    assert result == {"status": "ok"}
    assert call_count == 2


# ──────────────────────────────────────────────
# [FULL] 401 인증 실패 → 재시도 없이 즉시 예외
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.retry
async def test_no_retry_on_auth_error(gateway, patch_settings):
    """APIStatusError(401)는 재시도하지 않고 즉시 예외를 발생시켜야 합니다."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

    gateway.client.chat.completions.create = AsyncMock(
        side_effect=openai.AuthenticationError(
            "Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}},
        )
    )

    with pytest.raises(openai.AuthenticationError):
        await gateway.chat_json("System", {"test": "auth"}, "/test/auth")

    # API는 정확히 1번만 호출되어야 함 (재시도 없음)
    assert gateway.client.chat.completions.create.call_count == 1


# ──────────────────────────────────────────────
# [FULL] JSON 파싱 에러 → 재시도 후 정상 파싱
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.retry
async def test_retry_on_json_decode_error(gateway, patch_settings):
    """OpenAI가 깨진 JSON을 반환하면 재시도 후 정상 JSON을 받아야 합니다."""
    broken_response = _make_mock_response(content="NOT VALID JSON {{{")
    good_response = _make_mock_response(content='{"fixed": true}')
    call_count = 0

    async def mock_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return broken_response
        return good_response

    gateway.client.chat.completions.create = AsyncMock(side_effect=mock_effect)
    patch_settings.openai_max_retries = 1

    result = await gateway.chat_json("System", {"test": "json"}, "/test/json")

    assert result == {"fixed": True}
    assert call_count == 2


# ──────────────────────────────────────────────
# [FULL] 최대 재시도 횟수 초과 → 마지막 예외 raise
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.retry
async def test_exhausted_retries_raises(gateway, patch_settings):
    """모든 재시도가 실패하면 마지막 예외가 raise되어야 합니다."""
    gateway.client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
    )
    # max_retries=1 → 총 2번 시도 (초기 1 + 재시도 1)
    patch_settings.openai_max_retries = 1

    with pytest.raises(openai.RateLimitError):
        await gateway.chat_json("System", {"test": "exhaust"}, "/test/exhaust")

    assert gateway.client.chat.completions.create.call_count == 2
