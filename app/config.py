"""Application configuration.

All tunables are read from environment variables (or a local ``.env`` file)
so the same image can run unchanged in local dev, CI, and on the EC2 host.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Attributes:
        gemini_api_key: API key for Google AI Studio / Gemini. Required for
            real embedding + generation; tests run in ``offline_mode`` instead.
        embedding_model: Gemini embedding model id.
        generation_model: Gemini chat/generation model id.
        embedding_dim: Output dimensionality of ``embedding_model``. Used to
            size the FAISS index. ``text-embedding-004`` returns 768 floats.
        data_dir: Directory where the FAISS index + metadata are persisted.
        upload_dir: Directory where uploaded source files are stored.
        chunk_size: Target characters per text chunk before embedding.
        chunk_overlap: Characters shared between adjacent chunks for context.
        top_k: Number of nearest chunks retrieved per query.
        log_level: Root logging level (e.g. ``INFO``, ``DEBUG``).
        log_file: Path to the rotating log file.
        offline_mode: When true, no network calls are made to Gemini. Embeddings
            are produced by a deterministic local hash so the app and its tests
            run without an API key.
    """

    # pydantic-settings: load from environment and an optional .env file.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    embedding_model: str = "models/text-embedding-004"
    generation_model: str = "models/gemini-2.0-flash"
    embedding_dim: int = 768

    data_dir: str = "data"
    upload_dir: str = "data/uploads"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4

    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    offline_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton ``Settings`` instance.

    ``lru_cache`` ensures the environment is parsed only once per process and
    the same object is shared everywhere it is injected.

    Returns:
        The application :class:`Settings`.
    """
    return Settings()
