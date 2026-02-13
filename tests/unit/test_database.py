# tests/unit/test_database.py
import os

import pytest


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://maios:maios@localhost:5432/maios")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    # Clear the cached settings to force reload
    import maios.core.config as config_module

    config_module._settings = None
    yield
    # Clean up
    config_module._settings = None


@pytest.mark.asyncio
async def test_database_engine_creation():
    """Test that database engine can be created."""
    from maios.core.database import create_engine

    engine = create_engine("sqlite+aiosqlite:///:memory:")

    assert engine is not None
    assert engine.dialect.name == "sqlite"


@pytest.mark.asyncio
async def test_session_dependency():
    """Test session dependency yields session."""
    from maios.core.database import get_session

    # This would be tested with actual async context
    # For now, just verify the function exists
    assert callable(get_session)
