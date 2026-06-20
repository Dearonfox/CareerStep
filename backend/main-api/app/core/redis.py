import redis

from app.core.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def store_refresh_token(refresh_token: str, user_id: int, ttl_seconds: int) -> None:
    try:
        redis_client.setex(f"refresh:{refresh_token}", ttl_seconds, str(user_id))
    except redis.RedisError:
        pass


def delete_refresh_token(refresh_token: str) -> None:
    try:
        redis_client.delete(f"refresh:{refresh_token}")
    except redis.RedisError:
        pass


def get_refresh_token_user_id(refresh_token: str) -> int | None:
    try:
        user_id = redis_client.get(f"refresh:{refresh_token}")
    except redis.RedisError:
        return None
    return int(user_id) if user_id is not None else None
