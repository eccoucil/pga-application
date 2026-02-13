"""Application configuration using pydantic-settings."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    # OpenAI (optional - only required when using embedding features)
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Anthropic (for Claude Sonnet 4 reasoning)
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-20250514"

    # CRAWL4AI web crawler settings
    crawl4ai_max_pages: int = 50
    crawl4ai_timeout: int = 300  # 5 minutes

    # LlamaExtract (optional - for document extraction)
    llama_cloud_api_key: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings for testing."""
    global _settings
    _settings = None
