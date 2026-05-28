from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
