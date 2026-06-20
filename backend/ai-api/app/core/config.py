from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = "sk-change-me"
    openai_model: str = "gpt-4o-mini"
    openai_roadmap_model: str = ""  # 비어있으면 openai_model로 폴백
    internal_service_key: str = "change-me-internal-service-key"
    ai_log_db_path: str = "/data/ai_logs.sqlite3"
    max_tokens: int = 4000
    openai_rpm_limit: int = 200
    openai_tpm_limit: int = 80000
    openai_max_retries: int = 3
    openai_concurrency_limit: int = 5
    mongodb_uri: str = ""
    summarize_batch_size: int = 10


settings = Settings()
