"""
동시성 제어 테스트 (concurrency 범주)

smoke: Semaphore가 동시 실행 수를 정확히 제한하는지 검증
full:  RPM 슬라이딩 윈도우 차단 검증
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import _make_mock_response


# ──────────────────────────────────────────────
# [SMOKE] Semaphore 동시 실행 수 제한 검증
# ──────────────────────────────────────────────
@pytest.mark.smoke
@pytest.mark.concurrency
async def test_semaphore_limits_concurrent_calls(gateway, patch_settings):
    """concurrency_limit=2 일 때, 동시 실행 요청이 2개를 초과하지 않아야 합니다."""
    success_response = _make_mock_response()

    active_requests = 0
    max_active_observed = 0
    lock = asyncio.Lock()

    async def slow_mock_create(*args, **kwargs):
        nonlocal active_requests, max_active_observed
        async with lock:
            active_requests += 1
            if active_requests > max_active_observed:
                max_active_observed = active_requests

        await asyncio.sleep(0.3)  # 네트워크 대기 모사

        async with lock:
            active_requests -= 1
        return success_response

    gateway.client.chat.completions.create = AsyncMock(side_effect=slow_mock_create)

    # 5개의 요청을 동시에 발사 (concurrency_limit=2)
    tasks = [
        gateway.chat_json("System", {"id": i}, f"/test/concurrent_{i}")
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(r == {"status": "ok"} for r in results)
    assert max_active_observed <= 2, (
        f"Expected max concurrent <= 2, observed {max_active_observed}"
    )


# ──────────────────────────────────────────────
# [FULL] RPM 슬라이딩 윈도우 차단 검증
# ──────────────────────────────────────────────
@pytest.mark.full
@pytest.mark.concurrency
async def test_rpm_sliding_window_blocks(patch_settings):
    """RPM 한도에 도달하면 rate limiter가 새 요청을 일시 차단해야 합니다."""
    from app.gateway.rate_limiter import RateLimiter

    # RPM 2, 매우 높은 TPM으로 RPM만 테스트
    limiter = RateLimiter(rpm_limit=2, tpm_limit=999999, concurrency_limit=10)

    # 첫 2건은 즉시 통과해야 함
    await limiter.acquire(100)
    limiter.release()
    await limiter.acquire(100)
    limiter.release()

    # 3번째 요청은 RPM 한도 도달로 차단 → 타임아웃 내에 통과하지 않아야 함
    acquired = False

    async def try_acquire():
        nonlocal acquired
        await limiter.acquire(100)
        acquired = True
        limiter.release()

    try:
        await asyncio.wait_for(try_acquire(), timeout=1.0)
    except asyncio.TimeoutError:
        pass  # 예상대로 차단됨

    assert not acquired, "RPM limit reached but request was not blocked"
