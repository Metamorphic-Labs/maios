# tests/integration/test_agents_api.py
"""Integration tests for the Agents API."""

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

# Set up test environment before importing app
os.environ.setdefault("ZAI_API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/maios_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Reset cached settings before importing
import maios.core.config as config_module
import maios.core.redis as redis_module

config_module._settings = None
redis_module._pool = None

from maios.api.main import app
from maios.models.agent import Agent, AgentStatus


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock(spec=Agent)
    agent.id = uuid4()
    agent.name = "Test Agent"
    agent.role = "Developer"
    agent.persona = "A helpful coding assistant"
    agent.status = AgentStatus.IDLE
    agent.skill_tags = ["python", "testing"]
    agent.permissions = ["read", "write"]
    agent.performance_score = 0.95
    agent.current_task_id = None
    return agent


@pytest.fixture
async def client(mock_session):
    """Create an async test client with mocked database."""
    async def override_get_session():
        yield mock_session

    from maios.core.database import get_session
    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_agent(client, mock_session):
    """Test creating a new agent."""
    # Mock the session behavior
    created_agent = MagicMock(spec=Agent)
    created_agent.id = uuid4()
    created_agent.name = "Test Agent"
    created_agent.role = "Developer"
    created_agent.persona = "A helpful coding assistant"
    created_agent.status = AgentStatus.IDLE
    created_agent.skill_tags = ["python", "testing"]
    created_agent.permissions = ["read", "write"]
    created_agent.performance_score = 0.0
    created_agent.current_task_id = None

    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda a: setattr(a, 'id', created_agent.id))

    response = await client.post(
        "/api/agents",
        json={
            "name": "Test Agent",
            "role": "Developer",
            "persona": "A helpful coding assistant",
            "skill_tags": ["python", "testing"],
            "permissions": ["read", "write"],
        },
    )

    assert response.status_code == 201
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_agent_minimal(client, mock_session):
    """Test creating an agent with minimal data."""
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.post(
        "/api/agents",
        json={
            "name": "Minimal Agent",
            "role": "Worker",
            "persona": "Basic agent",
        },
    )

    assert response.status_code == 201
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_agents(client, mock_session):
    """Test listing all agents."""
    # Create mock agents
    agents = []
    for i in range(3):
        agent = MagicMock(spec=Agent)
        agent.id = uuid4()
        agent.name = f"List Test Agent {i}"
        agent.role = f"Role {i}"
        agent.persona = f"Persona {i}"
        agent.status = AgentStatus.IDLE
        agent.skill_tags = ["python"]
        agent.permissions = ["read"]
        agent.performance_score = 0.9
        agent.current_task_id = None
        agents.append(agent)

    # Mock the execute result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = agents
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get("/api/agents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Verify the response structure
    for agent in data:
        assert "id" in agent
        assert "name" in agent
        assert "status" in agent


@pytest.mark.asyncio
async def test_list_agents_with_status_filter(client, mock_session):
    """Test listing agents with status filter."""
    # Create mock agents with IDLE status
    agents = []
    for i in range(2):
        agent = MagicMock(spec=Agent)
        agent.id = uuid4()
        agent.name = f"Idle Agent {i}"
        agent.role = f"Role {i}"
        agent.persona = f"Persona {i}"
        agent.status = AgentStatus.IDLE
        agent.skill_tags = []
        agent.permissions = []
        agent.performance_score = 0.8
        agent.current_task_id = None
        agents.append(agent)

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = agents
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get(f"/api/agents?status={AgentStatus.IDLE.value}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # All returned agents should have IDLE status
    for agent in data:
        assert agent["status"] == AgentStatus.IDLE.value


@pytest.mark.asyncio
async def test_list_agents_with_pagination(client, mock_session):
    """Test listing agents with pagination."""
    agents = []
    for i in range(2):
        agent = MagicMock(spec=Agent)
        agent.id = uuid4()
        agent.name = f"Pagination Agent {i}"
        agent.role = f"Role {i}"
        agent.persona = f"Persona {i}"
        agent.status = AgentStatus.IDLE
        agent.skill_tags = []
        agent.permissions = []
        agent.performance_score = 0.7
        agent.current_task_id = None
        agents.append(agent)

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = agents
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get("/api/agents?skip=2&limit=2")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_agent(client, mock_session, mock_agent):
    """Test getting a specific agent by ID."""
    mock_session.get = AsyncMock(return_value=mock_agent)

    response = await client.get(f"/api/agents/{mock_agent.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mock_agent.id)
    assert data["name"] == mock_agent.name
    assert data["role"] == mock_agent.role
    assert data["persona"] == mock_agent.persona


@pytest.mark.asyncio
async def test_get_agent_not_found(client, mock_session):
    """Test getting a non-existent agent."""
    mock_session.get = AsyncMock(return_value=None)

    response = await client.get("/api/agents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Agent not found"


@pytest.mark.asyncio
async def test_update_agent(client, mock_session, mock_agent):
    """Test updating an agent."""
    mock_session.get = AsyncMock(return_value=mock_agent)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.patch(
        f"/api/agents/{mock_agent.id}",
        json={
            "name": "Updated Agent Name",
            "role": "Senior Developer",
            "status": AgentStatus.WORKING.value,
        },
    )

    assert response.status_code == 200
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_agent_partial(client, mock_session, mock_agent):
    """Test partially updating an agent."""
    mock_session.get = AsyncMock(return_value=mock_agent)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.patch(
        f"/api/agents/{mock_agent.id}",
        json={
            "name": "Partially Updated Name",
        },
    )

    assert response.status_code == 200
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_agent_not_found(client, mock_session):
    """Test updating a non-existent agent."""
    mock_session.get = AsyncMock(return_value=None)

    response = await client.patch(
        "/api/agents/00000000-0000-0000-0000-000000000000",
        json={"name": "This should fail"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Agent not found"
