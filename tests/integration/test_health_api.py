"""Tests for Health API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock


class TestSystemHealthEndpoint:
    """Tests for /api/health/status endpoint."""

    @pytest.mark.asyncio
    async def test_system_health_returns_status(self):
        """Test system health endpoint returns status."""
        from maios.api.main import app

        with patch("maios.api.routes.health_detailed.sandbox_manager") as mock_manager:
            mock_manager.is_healthy.return_value = True

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "database" in data["components"]
        assert "docker" in data["components"]

    @pytest.mark.asyncio
    async def test_system_health_includes_docker_status(self):
        """Test system health includes Docker status."""
        from maios.api.main import app

        with patch("maios.api.routes.health_detailed.sandbox_manager") as mock_manager:
            mock_manager.is_healthy.return_value = True

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/status")

        assert response.status_code == 200
        data = response.json()
        assert data["components"]["docker"]["status"] == "healthy"


class TestTaskHealthEndpoint:
    """Tests for /api/health/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_task_health_returns_status(self):
        """Test task health endpoint returns status."""
        from maios.api.main import app

        # Mock the async_session context manager
        mock_session = AsyncMock()

        # Mock the execute result for group by query
        mock_result = MagicMock()
        mock_result.all.return_value = []  # Empty status counts

        # Mock the execute result for active count
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_session.execute.side_effect = [mock_result, mock_count_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "by_status" in data
        assert "total" in data
        assert "active" in data

    @pytest.mark.asyncio
    async def test_task_health_counts_by_status(self):
        """Test task health counts tasks by status."""
        from maios.api.main import app
        from maios.models.task import TaskStatus

        mock_session = AsyncMock()

        # Mock group by result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (TaskStatus.COMPLETED, 5),
            (TaskStatus.PENDING, 2),
        ]

        # Mock active count
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_session.execute.side_effect = [mock_result, mock_count_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/tasks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["by_status"], dict)
        assert data["total"] == 7
        assert data["active"] == 2


class TestAgentHealthEndpoint:
    """Tests for /api/health/agents endpoint."""

    @pytest.mark.asyncio
    async def test_agent_health_returns_status(self):
        """Test agent health endpoint returns status."""
        from maios.api.main import app

        mock_session = AsyncMock()

        # Mock group by result
        mock_result = MagicMock()
        mock_result.all.return_value = []

        # Mock working count
        mock_working_result = MagicMock()
        mock_working_result.scalar.return_value = 0

        # Mock total count
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 0

        mock_session.execute.side_effect = [mock_result, mock_working_result, mock_total_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/agents")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "by_status" in data
        assert "total" in data
        assert "working" in data

    @pytest.mark.asyncio
    async def test_agent_health_counts_by_status(self):
        """Test agent health counts agents by status."""
        from maios.api.main import app
        from maios.models.agent import AgentStatus

        mock_session = AsyncMock()

        # Mock group by result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (AgentStatus.IDLE, 3),
            (AgentStatus.WORKING, 1),
        ]

        # Mock working count
        mock_working_result = MagicMock()
        mock_working_result.scalar.return_value = 1

        # Mock total count
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 4

        mock_session.execute.side_effect = [mock_result, mock_working_result, mock_total_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["working"] == 1


class TestContainerHealthEndpoint:
    """Tests for /api/health/containers endpoint."""

    @pytest.mark.asyncio
    async def test_container_health_returns_status(self):
        """Test container health endpoint returns status."""
        from maios.api.main import app

        with patch("maios.api.routes.health_detailed.sandbox_manager") as mock_manager:
            mock_manager.is_healthy.return_value = True
            mock_manager.list_active_containers.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/containers")

        assert response.status_code == 200
        data = response.json()
        assert "docker_available" in data
        assert "active_containers" in data
        assert "containers" in data

    @pytest.mark.asyncio
    async def test_container_health_handles_docker_unavailable(self):
        """Test container health handles Docker unavailable."""
        from maios.api.main import app

        with patch("maios.api.routes.health_detailed.sandbox_manager") as mock_manager:
            mock_manager.is_healthy.return_value = False
            mock_manager.list_active_containers.side_effect = Exception("Docker not available")

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/containers")

        assert response.status_code == 200
        data = response.json()
        assert data["docker_available"] is False
        assert "error" in data


class TestSystemMetricsEndpoint:
    """Tests for /api/health/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_returns_aggregated_data(self):
        """Test metrics endpoint returns aggregated data."""
        from maios.api.main import app

        mock_session = AsyncMock()

        # Mock task count result
        mock_task_result = MagicMock()
        mock_task_result.all.return_value = []

        # Mock agent aggregate result
        mock_agent_result = MagicMock()
        mock_agent_result.one.return_value = MagicMock(total=0, completed=0, failed=0)

        mock_session.execute.side_effect = [mock_task_result, mock_agent_result]

        with patch("maios.api.routes.health_detailed.sandbox_manager") as mock_manager:
            mock_manager.is_healthy.return_value = True

            with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
                mock_async_session.return_value.__aenter__.return_value = mock_session

                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.get("/api/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "tasks" in data
        assert "agents" in data
        assert "system" in data

    @pytest.mark.asyncio
    async def test_metrics_includes_task_counts(self):
        """Test metrics includes task counts."""
        from maios.api.main import app

        mock_session = AsyncMock()

        # Mock task count result
        mock_task_result = MagicMock()
        mock_task_result.all.return_value = []

        # Mock agent aggregate result
        mock_agent_result = MagicMock()
        mock_agent_result.one.return_value = MagicMock(total=0, completed=0, failed=0)

        mock_session.execute.side_effect = [mock_task_result, mock_agent_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "by_status" in data["tasks"]
        assert "total" in data["tasks"]

    @pytest.mark.asyncio
    async def test_metrics_includes_agent_stats(self):
        """Test metrics includes agent statistics."""
        from maios.api.main import app

        mock_session = AsyncMock()

        # Mock task count result
        mock_task_result = MagicMock()
        mock_task_result.all.return_value = []

        # Mock agent aggregate result
        mock_agent_result = MagicMock()
        mock_agent_result.one.return_value = MagicMock(total=5, completed=50, failed=5)

        mock_session.execute.side_effect = [mock_task_result, mock_agent_result]

        with patch("maios.api.routes.health_detailed.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_session

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["agents"]["total"] == 5
        assert data["agents"]["tasks_completed"] == 50
        assert data["agents"]["tasks_failed"] == 5
        assert "success_rate" in data["agents"]
