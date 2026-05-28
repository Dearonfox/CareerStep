from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_internal_key(x_internal_key: str = Header(default="")) -> None:
    if x_internal_key != settings.internal_service_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal service key",
        )
