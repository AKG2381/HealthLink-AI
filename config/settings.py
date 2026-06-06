"""
Configuration settings for HealthLink using Pydantic Settings.
All settings loaded from environment variables with sensible defaults.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration (Anthropic Claude via langchain-anthropic)
    anthropic_api_key: str = ""
    llm_model_name: str = "claude-sonnet-4-6"  # strong + cost-effective for structured output
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # Embedding Configuration (local HuggingFace model - no API key required)
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, CPU-friendly

    # Pinecone Configuration
    pinecone_api_key: str = ""
    pinecone_environment: str = ""  # e.g., "us-east-1-aws"
    pinecone_index_name: str = "healthlink"

    # RAG Configuration
    enable_rag: bool = True
    rag_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Database Configuration
    database_url: str = "sqlite:///./data/healthlink.db"
    db_echo: bool = False

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8501"]

    # Logging Configuration
    log_level: str = "INFO"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"

    # Google Cloud Configuration
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    cloud_run_service_name: str = "healthlink"

    # Feature Flags
    enable_metrics: bool = True

    def validate_config(self) -> None:
        """Validate required configuration is present."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        # Embeddings run locally (no key), but Pinecone still needs a key when RAG is on.
        if self.enable_rag and not self.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required when ENABLE_RAG is true")


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    FastAPI dependency for getting application settings.
    Returns singleton instance.

    Note: configuration is NOT validated here. Validating (and raising) at import
    time crash-loops the container on Cloud Run and breaks test collection before a
    single test runs. Validation happens lazily via `Settings.validate_config()`
    (called in the app lifespan, where a missing key is logged rather than fatal).
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings