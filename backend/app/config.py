"""Application settings loaded from environment / .env via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- Core ----
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # ---- Database ----
    # Async SQLAlchemy URL (postgresql+asyncpg://...). Alembic derives the sync URL.
    database_url: str = "postgresql+asyncpg://notebooklm:notebooklm@localhost:5432/notebooklm"

    # ---- Redis / Celery ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Clerk ----
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_audience: str = ""

    # ---- Supabase Storage ----
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "documents"

    # ---- LLM (OpenRouter) ----
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct"

    # ---- Embeddings + Rerank (NVIDIA Nemotron via OpenRouter) ----
    # Keys default to OPENROUTER_API_KEY (see effective_* properties) but can be overridden.
    embeddings_api_key: str = ""
    embeddings_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    embedding_dim: int = 1024
    rerank_api_key: str = ""
    rerank_base_url: str = "https://openrouter.ai/api/v1"
    rerank_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"

    # ---- Uploads ----
    max_upload_mb: int = 25

    # ---- Retrieval tuning ----
    retrieval_top_k: int = 40
    rerank_top_n: int = 8
    chunk_target_tokens: int = 512
    chunk_overlap_ratio: float = 0.2

    # ---- Monitoring ----
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """Sync (psycopg) URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def effective_embeddings_api_key(self) -> str:
        """Embeddings key, defaulting to the OpenRouter key when unset."""
        return self.embeddings_api_key or self.openrouter_api_key

    @property
    def effective_rerank_api_key(self) -> str:
        """Rerank key, defaulting to the OpenRouter key when unset."""
        return self.rerank_api_key or self.openrouter_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
