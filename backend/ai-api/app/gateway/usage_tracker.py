import logging
from app.core.logging import write_ai_usage

logger = logging.getLogger(__name__)

# OpenAI API 요금 테이블 (1M 토큰당 USD 요금 기준)
# 2026년 기준 표준 요금:
# - gpt-4o-mini: input $0.15 / 1M, output $0.60 / 1M
# - gpt-4o: input $2.50 / 1M, output $10.00 / 1M
MODEL_PRICING = {
    "gpt-4o-mini": {
        "input_price_per_token": 0.15 / 1_000_000,
        "output_price_per_token": 0.60 / 1_000_000,
    },
    "gpt-4o": {
        "input_price_per_token": 2.50 / 1_000_000,
        "output_price_per_token": 10.00 / 1_000_000,
    }
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    # 매핑되지 않은 모델은 기본적으로 gpt-4o-mini 단가로 계산
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_cost = prompt_tokens * pricing["input_price_per_token"]
    output_cost = completion_tokens * pricing["output_price_per_token"]
    return input_cost + output_cost

async def track_usage(
    endpoint: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    status: str,
    retry_count: int,
    latency_ms: int,
) -> float:
    total_tokens = prompt_tokens + completion_tokens
    estimated_cost = calculate_cost(model, prompt_tokens, completion_tokens)
    
    try:
        await write_ai_usage(
            endpoint=endpoint,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            status=status,
            retry_count=retry_count,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(f"Failed to write AI usage to DB: {e}")
        
    return estimated_cost
