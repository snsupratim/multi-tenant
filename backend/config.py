"""
config.py – Centralised settings loaded from .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # MongoDB
    mongodb_url: str
    mongodb_db_name: str = "rag_saas"

    # Pinecone
    pinecone_api_key: str
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "rag-saas-index"

    # Google Gemini
    google_api_key: str
    gemini_embedding_model: str = "models/embedding-001"

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Rate limiting
    rate_limit_per_minute: int = 20
    rate_limit_upload_per_day: int = 50

    # CORS
    allowed_origins: str = "http://localhost:8501"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
