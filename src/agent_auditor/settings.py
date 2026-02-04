"""
Application settings using Pydantic Settings.

Follows 12-Factor: all configuration from environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeminiSettings(BaseSettings):
    """Configuration for Gemini API adapter."""
    
    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        extra="ignore"
    )
    
    # API Configuration
    api_key: Optional[str] = None
    default_model: str = "gemini-1.5-flash"
    
    # Retry Configuration
    max_retries: int = 5
    base_retry_delay: float = 1.0
    
    # Rate Limits (Free Tier defaults)
    requests_per_minute: int = 15
    tokens_per_minute: int = 1_000_000
    requests_per_day: int = 1500


class SchedulerSettings(BaseSettings):
    """Configuration for ArbiterScheduler."""
    
    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        extra="ignore"
    )
    
    # Human reserve percentage
    human_reserve_percent: int = 30
    
    # Background processing
    batch_size: int = 10
    poll_interval_seconds: float = 5.0
    
    # Priority threshold (0=HUMAN, 1=CRITICAL, 2=HIGH, 3=NORMAL, 4=LOW, 5=BACKGROUND)
    # Tasks at or below this priority execute immediately
    immediate_priority_threshold: int = 2  # HIGH


class Settings(BaseSettings):
    """Root application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AGENT_AUDITOR_",
        extra="ignore"
    )
    
    # Database
    database_path: str = "agent_auditor.db"
    
    # Logging
    log_level: str = "INFO"
    
    # Nested settings
    gemini: GeminiSettings = GeminiSettings()
    scheduler: SchedulerSettings = SchedulerSettings()


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings, loading from environment."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
