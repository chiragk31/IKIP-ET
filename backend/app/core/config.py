"""
Application Configuration

Loads and validates all environment variables using pydantic-settings.
All configuration is accessed via the `settings` singleton.

Never hardcode configuration values. Always use environment variables.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All fields are validated by Pydantic on startup.
    Missing required fields will cause the application to fail immediately.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------
    # Application
    # ------------------------------------------
    APP_NAME: str = "IKIP Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------
    # API
    # ------------------------------------------
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ------------------------------------------
    # Supabase
    # ------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # ------------------------------------------
    # Google Gemini AI
    # ------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_TIMEOUT: int = 60

    # ------------------------------------------
    # Google Embeddings
    # ------------------------------------------
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # ------------------------------------------
    # Neo4j Aura (Knowledge Graph)
    # ------------------------------------------
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ------------------------------------------
    # Pinecone (Vector Database)
    # ------------------------------------------
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "ikip-documents"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"

    # ------------------------------------------
    # Inngest (Event-Driven Workflows)
    # ------------------------------------------
    INNGEST_SIGNING_KEY: str = ""
    INNGEST_EVENT_KEY: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Parse ALLOWED_ORIGINS from comma-separated string or list.
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    """
    Return cached settings singleton.
    Uses lru_cache to ensure only one instance is created.
    """
    return Settings()


# Global settings instance
settings = get_settings()
