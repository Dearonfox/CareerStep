"""
사용량 및 비용 기록 테스트 (tracking 범주)

smoke: 성공 호출 시 ai_usage에 토큰/비용 적재 확인
full:  retry_success 기록, 실패 기록, 모델별 단가 계산 정확성
"""
import pytest
import aiosqlite
from unittest.mock import AsyncMock, MagicMock
import openai

from tests.conftest import _make_mock_response
from app.gateway.usage_tracker import calculate_cost, MODEL_PRICING


# ──────────────────────────────────────────────
# [SMOKE] 성공 호출 시 ai_usage 테이블에 토큰/비용 기록 확인
# ──────────────────────────────────────────────
@pytest.mark.smoke
@pytest.mark.tracking
async def test_success_records_usage(gateway, patch_settings):
    """정상 API 호출이 완료되면 ai_usage 테이블에 토큰, 비용, status='success'가 기록되어야 합니다."""
    response = _make_mock_response(prompt_tokens=200, completion_tokens=80)
    gateway.client.chat.completions.create = AsyncMock(return_value=response)

    await gateway.chat_json("System", {"test": "track"}, "/test/track")

    # DB에서 직접 조회하여 검증
    async with aiosqlite.connect(patch_settings.ai_log_db_path) as db:
        cursor = await db.execute("SELECT * FROM ai_usage")
        rows = await cursor.fetchall()

    assert len(rows) == 1
    row = rows[0]
    # row 구조: (id, endpoint, model, prompt_tokens, completion_tokens, total_tokens,
    #            estimated_cost, status, retry_count, latency_ms, created_at)
    assert row[1] == "/test/track"        # endpoint
    assert row[2] == "gpt-4o-mini"        # model
    assert row[3] == 200                  # prompt_tokens
    assert row[4] == 80                   # completion_tokens
    assert row[5] == 280                  # total_tokens
    assert row[7] == "success"            # status
    assert row[8] == 0                    # retry_count
    assert row[6] > 0                     # estimated_cost > 0


# ──────────────────────────────────────────────
# [FULL] 재시도 성공 시 retry_success 상태 및 retry_count 기록
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.tracking
async def test_retry_success_records_count(gateway, patch_settings):
    """429 에러 후 재시도 성공하면 status='retry_success', retry_count=1이 기록되어야 합니다."""
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
    patch_settings.openai_max_retries = 1

    await gateway.chat_json("System", {"test": "retry_track"}, "/test/retry_track")

    async with aiosqlite.connect(patch_settings.ai_log_db_path) as db:
        cursor = await db.execute("SELECT status, retry_count FROM ai_usage")
        rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "retry_success"  # status
    assert rows[0][1] == 1               # retry_count


# ──────────────────────────────────────────────
# [FULL] 실패 건도 ai_usage에 failed 상태로 기록
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.tracking
async def test_failed_records_usage(gateway, patch_settings):
    """모든 재시도 실패 시 status='failed_exhausted_retries'가 기록되어야 합니다."""
    gateway.client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
    )
    patch_settings.openai_max_retries = 1

    with pytest.raises(openai.RateLimitError):
        await gateway.chat_json("System", {"test": "fail"}, "/test/fail")

    async with aiosqlite.connect(patch_settings.ai_log_db_path) as db:
        cursor = await db.execute("SELECT status FROM ai_usage")
        rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "failed_exhausted_retries"


# ──────────────────────────────────────────────
# [FULL] 모델별 단가 계산 정확성 검증
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.tracking
def test_cost_calculation_by_model():
    """gpt-4o-mini와 gpt-4o의 토큰 비용 계산이 단가표와 일치해야 합니다."""
    # gpt-4o-mini: input $0.15/1M, output $0.60/1M
    cost_mini = calculate_cost("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    expected_mini = 0.15 + 0.60
    assert abs(cost_mini - expected_mini) < 1e-9, f"gpt-4o-mini cost: {cost_mini} != {expected_mini}"

    # gpt-4o: input $2.50/1M, output $10.00/1M
    cost_4o = calculate_cost("gpt-4o", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    expected_4o = 2.50 + 10.00
    assert abs(cost_4o - expected_4o) < 1e-9, f"gpt-4o cost: {cost_4o} != {expected_4o}"

    # 알 수 없는 모델은 gpt-4o-mini 단가로 폴백
    cost_unknown = calculate_cost("gpt-unknown", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert abs(cost_unknown - expected_mini) < 1e-9, "Unknown model should fallback to gpt-4o-mini pricing"
