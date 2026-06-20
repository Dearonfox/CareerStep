import json
import time
import asyncio
import logging
from app.core.config import settings
from app.core.logging import write_ai_log
from app.gateway.rate_limiter import RateLimiter
from app.gateway.usage_tracker import track_usage
import openai
from pydantic import BaseModel

class GatewayError(Exception):
    pass

logger = logging.getLogger(__name__)

class GPTGateway:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.rate_limiter = RateLimiter(
            rpm_limit=settings.openai_rpm_limit,
            tpm_limit=settings.openai_tpm_limit,
            concurrency_limit=settings.openai_concurrency_limit
        )

    async def chat_json(
        self,
        system_prompt: str,
        payload: dict,
        endpoint: str,
        response_format: type[BaseModel],
        model: str = None,
        estimated_tokens: int = 1500,
        max_output_tokens: int = None,
    ) -> dict:
        """
        OpenAI Chat Completions API를 JSON 모드로 호출합니다.
        동시성 및 Rate Limit을 제어하고, 일시적인 에러에 대해 재시도하며, 사용량과 비용을 기록합니다.
        max_output_tokens: 지정하면 settings.max_tokens 대신 이 값을 출력 토큰 한도로 사용.
        """
        model = model or settings.openai_model
        max_retries = settings.openai_max_retries
        output_tokens = max_output_tokens or settings.max_tokens
        
        last_exception = None
        start_time = time.time()
        
        for attempt in range(1, max_retries + 2):
            # 1. Rate Limiter에서 권한 획득 (Semaphore 포함)
            await self.rate_limiter.acquire(estimated_tokens)
            attempt_start = time.time()
            try:
                response = await self.client.beta.chat.completions.parse(
                    model=model,
                    response_format=response_format,
                    max_completion_tokens=output_tokens,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": json.dumps({"input": payload}, ensure_ascii=False),
                        },
                    ],
                )
                
                msg = response.choices[0].message
                finish = response.choices[0].finish_reason

                if msg.refusal:
                    raise GatewayError(f"model refused: {msg.refusal}")
                if msg.parsed is None:
                    raise GatewayError(f"structured parse failed (finish_reason={finish})")

                result = msg.parsed.model_dump(mode="json")
                
                # 성공 시 정보 처리
                latency_ms = int((time.time() - start_time) * 1000)
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else estimated_tokens
                completion_tokens = usage.completion_tokens if usage else 0
                
                # 실제 토큰 사용량으로 업데이트
                await self.rate_limiter.update_tokens(estimated_tokens, prompt_tokens + completion_tokens)
                
                # 로그 및 사용량 기록 (비동기 처리)
                await write_ai_log(endpoint, payload, result)
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    status="success" if attempt == 1 else "retry_success",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                
                return result

            except (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                last_exception = e
                latency_ms = int((time.time() - attempt_start) * 1000)
                logger.warning(
                    f"Retryable error on endpoint {endpoint} (attempt {attempt}/{max_retries + 1}): {e}"
                )
                
                # 실패 건에 대해서는 토큰 사용량을 0으로 환원하여 rate limiter에 과평가된 할당 해제
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                if attempt <= max_retries:
                    # Exponential Backoff 적용: wait 2^attempt 초 + jitter
                    sleep_time = (2 ** attempt) + (time.time() % 1.0)
                    await asyncio.sleep(sleep_time)
                else:
                    break
            except openai.APIStatusError as e:
                # 4xx 클라이언트 에러 (예: 잘못된 파라미터, API 키 인증 실패 등) -> 재시도 없이 즉시 실패
                latency_ms = int((time.time() - start_time) * 1000)
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    status="failed_client_error",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                logger.error(f"Client error on endpoint {endpoint} (no retry): {e}")
                raise e
            except Exception as e:
                # 기타 잡히지 않은 런타임 에러 -> 재시도 없음
                latency_ms = int((time.time() - start_time) * 1000)
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    status="failed_unknown_error",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                logger.error(f"Unknown error on endpoint {endpoint} (no retry): {e}")
                raise e
            finally:
                # 시도 건에 대한 Semaphore 자원 반환
                self.rate_limiter.release()

        # 재시도 횟수 초과 실패 처리
        latency_ms = int((time.time() - start_time) * 1000)
        await track_usage(
            endpoint=endpoint,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            status="failed_exhausted_retries",
            retry_count=max_retries,
            latency_ms=latency_ms,
        )
        logger.error(f"Exhausted all retries for endpoint {endpoint}. Last error: {last_exception}")
        raise last_exception

    async def chat_vision_json(
        self,
        system_prompt: str,
        text_payload: dict,
        image_urls: list[str],
        endpoint: str,
        response_format: type[BaseModel],
        model: str = None,
        estimated_tokens: int = 3000,
    ) -> dict:
        """OpenAI Vision API를 JSON 모드로 호출합니다."""
        model = model or "gpt-4.1-mini"  # gpt-4.1-mini 사용
        max_retries = settings.openai_max_retries
        
        last_exception = None
        start_time = time.time()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": json.dumps({"input": text_payload}, ensure_ascii=False)},
                ]
            }
        ]
        for url in image_urls:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {"url": url, "detail": "high"}
            })

        for attempt in range(1, max_retries + 2):
            await self.rate_limiter.acquire(estimated_tokens)
            attempt_start = time.time()
            try:
                response = await self.client.beta.chat.completions.parse(
                    model=model,
                    response_format=response_format,
                    max_tokens=settings.max_tokens,
                    temperature=0.2,
                    messages=messages,
                )
                
                msg = response.choices[0].message
                finish = response.choices[0].finish_reason

                if msg.refusal:
                    raise GatewayError(f"model refused: {msg.refusal}")
                if msg.parsed is None:
                    raise GatewayError(f"structured parse failed (finish_reason={finish})")

                result = msg.parsed.model_dump(mode="json")
                
                latency_ms = int((time.time() - start_time) * 1000)
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else estimated_tokens
                completion_tokens = usage.completion_tokens if usage else 0
                
                await self.rate_limiter.update_tokens(estimated_tokens, prompt_tokens + completion_tokens)
                
                # 로그 및 사용량 기록 (vision도 동일하게 기록)
                await write_ai_log(endpoint, text_payload, result)
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    status="success" if attempt == 1 else "retry_success",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                
                return result

            except (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                last_exception = e
                latency_ms = int((time.time() - attempt_start) * 1000)
                logger.warning(f"Retryable error on endpoint {endpoint} (attempt {attempt}/{max_retries + 1}): {e}")
                
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                if attempt <= max_retries:
                    sleep_time = (2 ** attempt) + (time.time() % 1.0)
                    await asyncio.sleep(sleep_time)
                else:
                    break
            except openai.APIStatusError as e:
                latency_ms = int((time.time() - start_time) * 1000)
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    status="failed_client_error",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                logger.error(f"Client error on endpoint {endpoint} (no retry): {e}")
                raise e
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                await self.rate_limiter.update_tokens(estimated_tokens, 0)
                
                await track_usage(
                    endpoint=endpoint,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    status="failed_unknown_error",
                    retry_count=attempt - 1,
                    latency_ms=latency_ms,
                )
                logger.error(f"Unknown error on endpoint {endpoint} (no retry): {e}")
                raise e
            finally:
                self.rate_limiter.release()

        latency_ms = int((time.time() - start_time) * 1000)
        await track_usage(
            endpoint=endpoint,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            status="failed_exhausted_retries",
            retry_count=max_retries,
            latency_ms=latency_ms,
        )
        logger.error(f"Exhausted all retries for endpoint {endpoint}. Last error: {last_exception}")
        raise last_exception

