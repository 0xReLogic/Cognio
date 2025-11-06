"""Configuration management for MemoryMCP."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    db_path: str = "./data/memory.db"

    # Embeddings
    embed_model: str = "paraphrase-multilingual-mpnet-base-v2"
    embed_device: str = "cpu"
    embedding_cache_path: str = "./data/embedding_cache.pkl"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_key: str | None = None

    # Search
    default_search_limit: int = 5
    similarity_threshold: float = 0.7

    # Performance
    max_text_length: int = 10000
    batch_size: int = 32
    summarize_threshold: int = 50

    # Logging
    log_level: str = "info"

    # Auto-tagging
    autotag_enabled: bool = False
    llm_provider: str = "groq"  # Options: "groq", "openai", "local"
    
    # OpenAI settings
    openai_api_key: str | None = None
    openai_model: str = "gpt-3.5-turbo"
    
    # Groq settings
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"  # or "llama-3.1-70b-versatile", "gemma2-9b-it"
    
    # Summarization
    summarization_enabled: bool = True
    summarization_method: str = "extractive"  # Options: "extractive", "abstractive"

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
