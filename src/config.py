"""Configuration management for MemoryMCP."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    db_path: str = "./data/memory.db"

    # Embeddings
    embed_model: str = "all-MiniLM-L6-v2"
    embed_device: str = "cpu"
    embedding_cache_path: str = "./data/embedding_cache.pkl"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_key: str | None = None

    # Search
    default_search_limit: int = 5
    similarity_threshold: float = 0.4
    hybrid_enabled: bool = False
    hybrid_alpha: float = 0.6
    hybrid_mode: str = "candidate"  # candidate | rerank
    hybrid_rerank_topk: int = 100

    # Engram O(1) retrieval (hashed N-gram index)
    engram_enabled: bool = True
    engram_ngram_sizes: str = "2,3"
    engram_num_heads: int = 4
    engram_num_buckets: int = 1000003
    engram_candidate_limit: int = 200
    engram_min_hits: int = 2
    engram_query_bucket_limit: int = 500

    # LEANN vector search (optional)
    leann_enabled: bool = False
    leann_index_path: str = "./data/leann/memories.leann"
    leann_backend: str = "hnsw"
    leann_lazy_build: bool = True
    leann_recompute_on_search: bool = True
    leann_warmup_on_start: bool = False

    # Performance
    max_text_length: int = 10000
    batch_size: int = 32
    summarize_threshold: int = 50

    # Logging
    log_level: str = "info"

    # Auto-tagging
    autotag_enabled: bool = True
    llm_provider: str = "groq"

    # OpenAI settings
    openai_api_key: str | None = None
    openai_model: str = "gpt-3.5-turbo"

    # Groq settings
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # Summarization
    summarization_enabled: bool = True
    summarization_method: str = "abstractive"
    summarization_embed_model: str = "all-MiniLM-L6-v2"

    # Re-embedding
    auto_reembed_on_start: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_db_dir(self) -> Path:
        """Get database directory path."""
        return Path(self.db_path).parent

    def ensure_db_dir(self) -> None:
        """Create database directory if it doesn't exist."""
        db_dir = self.get_db_dir()
        db_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
