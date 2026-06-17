import asyncio
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rpm_limit: int, tpm_limit: int, concurrency_limit: int):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        
        # Deque for request timestamps (RPM)
        self.request_times = deque()
        # Deque for token usage (timestamp, tokens) (TPM)
        self.token_usages = deque()
        
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1500):
        # 동시성 제한을 위한 Semaphore 획득
        await self.semaphore.acquire()
        try:
            while True:
                async with self.lock:
                    now = time.time()
                    
                    # 60초가 지난 오래된 기록 정리
                    while self.request_times and self.request_times[0] < now - 60:
                        self.request_times.popleft()
                    while self.token_usages and self.token_usages[0][0] < now - 60:
                        self.token_usages.popleft()
                        
                    current_rpm = len(self.request_times)
                    current_tpm = sum(tokens for _, tokens in self.token_usages)
                    
                    # RPM 및 TPM 제한 검사
                    if current_rpm < self.rpm_limit and (current_tpm + estimated_tokens) <= self.tpm_limit:
                        self.request_times.append(now)
                        # 임시로 추정된 토큰 사용량 등록 (완료 시 실제 값으로 교정)
                        self.token_usages.append((now, estimated_tokens))
                        return
                    
                    logger.warning(
                        f"Rate limit hit. Current RPM: {current_rpm}/{self.rpm_limit}, "
                        f"TPM: {current_tpm + estimated_tokens}/{self.tpm_limit}. Waiting..."
                    )
                    
                # 제한에 걸리면 잠시 대기 후 재시도
                await asyncio.sleep(0.5)
        except Exception as e:
            self.semaphore.release()
            logger.error(f"Error during rate limiter acquire: {e}")
            raise

    def release(self):
        # Semaphore 해제
        self.semaphore.release()

    async def update_tokens(self, estimated_tokens: int, actual_tokens: int):
        # 완료 시점에 예측 토큰량을 실제 소모된 토큰량으로 업데이트
        async with self.lock:
            if self.token_usages:
                for i in reversed(range(len(self.token_usages))):
                    ts, tokens = self.token_usages[i]
                    if tokens == estimated_tokens:
                        self.token_usages[i] = (ts, actual_tokens)
                        break
