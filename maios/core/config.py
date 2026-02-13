# maios/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Z.ai Configuration
    zai_api_key: str
    default_model: str = "glm-4-plus"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Application
    task_timeout_minutes: int = 30
    multi_tenant_mode: bool = False
    log_level: str = "INFO"

    # Multi-tenancy (cloud mode)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


# Global settings instance (lazy-loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# For backward compatibility, expose settings as a property-like access
class _SettingsProxy:
    """Proxy to allow lazy loading of settings while maintaining simple access pattern."""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()  # type: ignore
