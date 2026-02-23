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
    # Question generation model (can be overridden for speed: claude-3-5-haiku-20241022 is 3-5x faster but lower quality)
    # NOTE: Haiku is significantly faster but produces lower-quality questions. Use only for quick iterations.
    question_generation_model: Optional[str] = None  # Defaults to claude_model if not set

    # Neo4j (optional - knowledge graph)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: Optional[str] = None

    # Qdrant (optional - vector search)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

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
