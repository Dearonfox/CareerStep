from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = "sk-change-me"
    openai_model: str = "gpt-4o-mini"
    internal_service_key: str = "change-me-internal-service-key"
    ai_log_db_path: str = "/data/ai_logs.sqlite3"
    max_tokens: int = 1500


settings = Settings()
