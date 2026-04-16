from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # WhatsApp Cloud API
    whatsapp_phone_id: str = ""
    whatsapp_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_id: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://kisan:password@localhost:5432/kisanai"
    redis_url: str = "redis://localhost:6379/0"

    # LLM fallback
    gemini_api_key: str = ""
    xai_api_key: str = ""

    # App
    app_env: str = "development"
    app_port: int = 8000
    log_level: str = "INFO"
    admin_username: str = "admin"
    admin_password: str = "changeme"

    # Agmarknet
    agmarknet_api_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
