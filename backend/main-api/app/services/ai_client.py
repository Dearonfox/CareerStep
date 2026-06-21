import httpx
from fastapi import HTTPException, status

from app.core.config import settings


async def post_to_ai_service(path: str, payload: dict) -> dict:
    headers = {"X-Internal-Key": settings.internal_service_key}
    url = f"{settings.ai_service_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable",
        ) from exc

async def get_from_ai_service(path: str, params: dict = None) -> dict:
    headers = {"X-Internal-Key": settings.internal_service_key}
    url = f"{settings.ai_service_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable",
        ) from exc
