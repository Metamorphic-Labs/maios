# tests/unit/test_config.py
import pytest
from pydantic import ValidationError


def test_config_defaults():
    """Test configuration loads with defaults."""
    from maios.core.config import Settings

    settings = Settings(
        zai_api_key="test-key",
        database_url="postgresql://localhost/maios",
        redis_url="redis://localhost/6379/0",
    )

    assert settings.default_model == "glm-4-plus"
    assert settings.task_timeout_minutes == 30
    assert settings.multi_tenant_mode is False
    assert settings.log_level == "INFO"


def test_config_requires_api_key():
    """Test that API key is required."""
    from maios.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/maios",
            redis_url="redis://localhost/6379/0",
        )
