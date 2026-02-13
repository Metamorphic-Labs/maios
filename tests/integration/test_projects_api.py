# tests/integration/test_projects_api.py
"""Integration tests for the Projects API."""

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
from maios.models.project import Project, ProjectStatus


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_project():
    """Create a mock project for testing."""
    project = MagicMock(spec=Project)
    project.id = uuid4()
    project.name = "Test Project"
    project.description = "A test project for testing"
    project.status = ProjectStatus.PLANNING
    project.initial_request = "Build a test application"
    project.tech_stack = ["python", "fastapi"]
    project.orchestrator_phase = "PLAN"
    project.created_at = "2024-01-01T00:00:00"
    project.updated_at = "2024-01-01T00:00:00"
    return project


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
async def test_create_project(client, mock_session):
    """Test creating a new project."""
    # Mock the session behavior
    created_project = MagicMock(spec=Project)
    created_project.id = uuid4()
    created_project.name = "Test Project"
    created_project.description = "A test project for testing"
    created_project.status = ProjectStatus.PLANNING
    created_project.initial_request = "Build a test application"
    created_project.tech_stack = ["python", "fastapi"]
    created_project.constraints = {"max_budget": 1000}
    created_project.orchestrator_phase = "PLAN"
    created_project.created_at = "2024-01-01T00:00:00"
    created_project.updated_at = "2024-01-01T00:00:00"

    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda p: setattr(p, 'id', created_project.id))

    response = await client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "description": "A test project for testing",
            "initial_request": "Build a test application",
            "tech_stack": ["python", "fastapi"],
            "constraints": {"max_budget": 1000},
        },
    )

    assert response.status_code == 201
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_project_minimal(client, mock_session):
    """Test creating a project with minimal data."""
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.post(
        "/api/projects",
        json={
            "name": "Minimal Project",
        },
    )

    assert response.status_code == 201
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_projects(client, mock_session):
    """Test listing all projects."""
    # Create mock projects
    projects = []
    for i in range(3):
        project = MagicMock(spec=Project)
        project.id = uuid4()
        project.name = f"List Test Project {i}"
        project.description = f"Description {i}"
        project.status = ProjectStatus.PLANNING
        project.initial_request = None
        project.tech_stack = []
        project.orchestrator_phase = "PLAN"
        project.created_at = "2024-01-01T00:00:00"
        project.updated_at = "2024-01-01T00:00:00"
        projects.append(project)

    # Mock the execute result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = projects
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Verify the response structure
    for project in data:
        assert "id" in project
        assert "name" in project
        assert "status" in project


@pytest.mark.asyncio
async def test_list_projects_with_status_filter(client, mock_session):
    """Test listing projects with status filter."""
    # Create mock projects with PLANNING status
    projects = []
    for i in range(2):
        project = MagicMock(spec=Project)
        project.id = uuid4()
        project.name = f"Planning Project {i}"
        project.description = None
        project.status = ProjectStatus.PLANNING
        project.initial_request = None
        project.tech_stack = []
        project.orchestrator_phase = "PLAN"
        project.created_at = "2024-01-01T00:00:00"
        project.updated_at = "2024-01-01T00:00:00"
        projects.append(project)

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = projects
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get(f"/api/projects?status={ProjectStatus.PLANNING.value}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # All returned projects should have PLANNING status
    for project in data:
        assert project["status"] == ProjectStatus.PLANNING.value


@pytest.mark.asyncio
async def test_list_projects_with_pagination(client, mock_session):
    """Test listing projects with pagination."""
    projects = []
    for i in range(2):
        project = MagicMock(spec=Project)
        project.id = uuid4()
        project.name = f"Pagination Project {i}"
        project.description = None
        project.status = ProjectStatus.PLANNING
        project.initial_request = None
        project.tech_stack = []
        project.orchestrator_phase = "PLAN"
        project.created_at = "2024-01-01T00:00:00"
        project.updated_at = "2024-01-01T00:00:00"
        projects.append(project)

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = projects
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    response = await client.get("/api/projects?skip=2&limit=2")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_project(client, mock_session, mock_project):
    """Test getting a specific project by ID."""
    mock_session.get = AsyncMock(return_value=mock_project)

    response = await client.get(f"/api/projects/{mock_project.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mock_project.id)
    assert data["name"] == mock_project.name
    assert data["description"] == mock_project.description


@pytest.mark.asyncio
async def test_get_project_not_found(client, mock_session):
    """Test getting a non-existent project."""
    mock_session.get = AsyncMock(return_value=None)

    response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_update_project(client, mock_session, mock_project):
    """Test updating a project."""
    mock_session.get = AsyncMock(return_value=mock_project)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.patch(
        f"/api/projects/{mock_project.id}",
        json={
            "name": "Updated Project Name",
            "description": "Updated description",
            "status": ProjectStatus.ACTIVE.value,
        },
    )

    assert response.status_code == 200
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_partial(client, mock_session, mock_project):
    """Test partially updating a project."""
    mock_session.get = AsyncMock(return_value=mock_project)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    response = await client.patch(
        f"/api/projects/{mock_project.id}",
        json={
            "name": "Partially Updated Name",
        },
    )

    assert response.status_code == 200
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_project_not_found(client, mock_session):
    """Test updating a non-existent project."""
    mock_session.get = AsyncMock(return_value=None)

    response = await client.patch(
        "/api/projects/00000000-0000-0000-0000-000000000000",
        json={"name": "This should fail"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Project not found"
