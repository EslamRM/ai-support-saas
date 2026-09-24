"""
Responsibility: centralized, typed application settings (Pydantic BaseSettings).

Everything environment-dependent (DB URL, Redis URL, Qdrant URL, JWT secret,
OPENAI_API_KEY, model names, chunk size, top-K, rate limits) is read from env
vars here and nowhere else. No module should call os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg2://app:app@localhost:5432/support_saas"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"

    # --- Auth ---
    jwt_secret_key: str = "change-me-in-real-deployments"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- LLM provider (abstracted -- see docs/adr/ADR-009 once written) ---
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = 20.0
    ai_max_attempts: int = 3
    ai_retry_base_delay_seconds: float = 0.25
    ai_retry_max_delay_seconds: float = 2.0

    # --- RAG tuning (see docs/rag.md, added Phase 4) ---
    chunk_size: int = 800
    chunk_overlap: int = 150
    retrieval_top_k: int = 5
    retrieval_similarity_threshold: float = 0.7
    retrieval_timeout_seconds: float = 5.0

    # --- Background jobs ---
    # False in production (real worker process consumes from Redis).
    # Tests set CELERY_TASK_ALWAYS_EAGER=true so `.delay()` runs the task
    # synchronously in-process -- no Redis/worker needed to test the
    # ingestion pipeline end-to-end. See tests/conftest.py.
    celery_task_always_eager: bool = False

    # --- File upload limits ---
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    rate_limit_per_minute: int = 60
    cors_origins: str = "http://localhost:5173"
    allowed_upload_content_types: tuple[str, ...] = (
        "text/plain",
        "text/markdown",
        "application/pdf",
    )


settings = Settings()
