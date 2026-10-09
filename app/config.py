"""Runtime configuration, read from environment variables so deployments need no code changes."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by default; set DATABASE_URL to a postgresql:// URL to switch databases.
    database_url: str = "sqlite:///./cache.db"
    # Simulated latency of the external transformer service.
    transformer_delay_seconds: float = Field(default=0.0, ge=0)
