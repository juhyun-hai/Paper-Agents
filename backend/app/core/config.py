"""
Application configuration using Pydantic Settings.
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://research_agent:research_pass_2024@localhost:5432/research_intelligence",
        description="PostgreSQL database URL"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis cache URL"
    )
    redis_password: Optional[str] = Field(default=None)

    # AI Services
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    huggingface_api_key: Optional[str] = Field(default=None)

    # Embedding Configuration
    embedding_model: str = Field(default="BAAI/bge-m3")
    embedding_dimension: int = Field(default=1024)
    batch_size: int = Field(default=32)
    max_tokens: int = Field(default=512)

    # Search Configuration
    default_search_limit: int = Field(default=20)
    max_search_limit: int = Field(default=100)
    similarity_threshold: float = Field(default=0.7)

    # Graph Configuration
    default_graph_depth: int = Field(default=3)
    max_graph_nodes: int = Field(default=1000)
    graph_layout: str = Field(default="force")

    # Cache Configuration (seconds)
    cache_ttl_search: int = Field(default=300)  # 5 minutes
    cache_ttl_embeddings: int = Field(default=3600)  # 1 hour
    cache_ttl_graph: int = Field(default=1800)  # 30 minutes

    # Rate Limiting
    arxiv_rate_limit: int = Field(default=3)  # requests per second
    requests_per_second: int = Field(default=10)

    # Development
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    # Export Configuration
    obsidian_vault_path: str = Field(default="/tmp/research_vault")
    max_export_papers: int = Field(default=100)

    # CORS Configuration
    allowed_origins: List[str] = Field(default=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "https://hotpaper.ai",
        "https://www.hotpaper.ai",
        "https://hotpaper.pages.dev",
        "https://*.hotpaper.pages.dev",
        "https://paper-agent-eight.vercel.app",
        "https://*.trycloudflare.com"
    ])
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = Field(default=["*"])

    @property
    def async_database_url(self) -> str:
        """Get async version of database URL."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")


# Global settings instance
settings = Settings()