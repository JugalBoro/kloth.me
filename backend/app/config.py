from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "fashion_search"
    
    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "fashion_products"
    qdrant_api_key: Optional[str] = None
    qdrant_use_https: bool = False
    
    # Google Gemini Configuration
    google_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    
    # Model Configuration
    clip_model_name: str = "openai/clip-vit-base-patch32"
    embedding_dimension: int = 512
    
    # Search Configuration
    default_top_k: int = 20
    text_weight: float = 0.5
    
    # Dataset Configuration
    dataset_name: str = "Marqo/fashion200k"
    sample_size: int = 5000
    random_seed: int = 42
    
    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
