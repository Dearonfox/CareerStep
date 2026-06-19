import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS = [
    "https://career-step.vercel.app",
    "https://career-step-git-main-elodef.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4281",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://careerstep:careerstep_password@mysql:3306/careerstep"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = "change-me-main-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    ai_service_url: str = "http://ai-backend:8001/api/v1"
    internal_service_key: str = "change-me-internal-service-key"
    cors_origins: list[str] = DEFAULT_CORS_ORIGINS

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str] | object:
        if not isinstance(value, str):
            return value

        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
        except json.JSONDecodeError:
            pass

        return [origin.strip() for origin in value.split(",") if origin.strip()]


settings = Settings()
