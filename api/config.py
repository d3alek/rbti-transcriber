"""Configuration management for the web API."""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Audio processing settings
    audio_directory: Path = Path("test_audio")
    config_file: Path = Path("config.yaml")
    
    # GitHub publishing settings
    github_repository_url: Optional[str] = None
    github_token: Optional[str] = None
    github_branch: str = "gh-pages"
    github_base_url: Optional[str] = None
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        env_prefix = "TRANSCRIPTION_"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()