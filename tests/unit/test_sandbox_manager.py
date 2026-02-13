"""Tests for Sandbox Manager."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestSandboxModels:
    """Tests for sandbox models."""

    def test_execution_request_defaults(self):
        """Test ExecutionRequest default values."""
        from maios.sandbox.models import ExecutionRequest

        request = ExecutionRequest(language="python", code="print('hello')")

        assert request.language == "python"
        assert request.code == "print('hello')"
        assert request.context_files == []
        assert request.environment == {}
        assert request.timeout_seconds == 30

    def test_execution_result_is_success(self):
        """Test ExecutionResult.is_success method."""
        from maios.sandbox.models import ExecutionResult

        success = ExecutionResult(exit_code=0, stdout="ok", stderr="", duration_ms=100)
        assert success.is_success() is True

        failure = ExecutionResult(exit_code=1, stdout="", stderr="error", duration_ms=100)
        assert failure.is_success() is False

        with_error = ExecutionResult(exit_code=0, stdout="", stderr="", duration_ms=100, error="some error")
        assert with_error.is_success() is False

    def test_container_type_enum(self):
        """Test ContainerType enum values."""
        from maios.sandbox.models import ContainerType

        assert ContainerType.EXECUTION.value == "execution"
        assert ContainerType.TEST_RUNNER.value == "test_runner"
        assert ContainerType.PREVIEW.value == "preview"

    def test_container_metrics_from_docker_stats(self):
        """Test ContainerMetrics.from_docker_stats."""
        from maios.sandbox.models import ContainerMetrics

        stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 200},
                "system_cpu_usage": 1000,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 100},
                "system_cpu_usage": 500,
            },
            "memory_stats": {
                "usage": 52428800,  # 50 MB
            },
            "networks": {
                "eth0": {"rx_bytes": 1024, "tx_bytes": 512},
            },
        }

        metrics = ContainerMetrics.from_docker_stats("test-id", stats)

        assert metrics.container_id == "test-id"
        assert metrics.memory_mb > 0
        assert metrics.network_rx_bytes == 1024
        assert metrics.network_tx_bytes == 512


class TestSandboxManager:
    """Tests for SandboxManager class."""

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        client = MagicMock()
        client.ping.return_value = True
        return client

    def test_sandbox_manager_initialization(self, mock_docker_client):
        """Test SandboxManager can be initialized."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager

            manager = SandboxManager()
            # Force client initialization
            _ = manager.client

            assert manager is not None
            assert manager._client is not None

    def test_sandbox_manager_health_check(self, mock_docker_client):
        """Test SandboxManager health check."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager

            manager = SandboxManager()
            _ = manager.client  # Force initialization

            assert manager.is_healthy() is True

    def test_sandbox_manager_unhealthy(self):
        """Test SandboxManager handles unhealthy Docker."""
        with patch("docker.from_env") as mock_from_env:
            from docker.errors import DockerException
            from maios.sandbox.manager import SandboxManager

            mock_from_env.side_effect = DockerException("Cannot connect")

            manager = SandboxManager()
            assert manager.is_healthy() is False

    def test_get_image_for_language(self, mock_docker_client):
        """Test getting image for supported languages."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager

            manager = SandboxManager()

            assert manager._get_image("python") == "python:3.12-slim"
            assert manager._get_image("javascript") == "node:20-slim"
            assert manager._get_image("typescript") == "node:20-slim"
            assert manager._get_image("unknown") is None

    def test_build_command_python(self, mock_docker_client):
        """Test building command for Python."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager

            manager = SandboxManager()
            cmd = manager._build_command("python", "print('hello')")

            assert cmd == ["python", "-c", "print('hello')"]

    def test_build_command_javascript(self, mock_docker_client):
        """Test building command for JavaScript."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager

            manager = SandboxManager()
            cmd = manager._build_command("javascript", "console.log('hello')")

            assert cmd == ["node", "-e", "console.log('hello')"]


class TestSandboxManagerExecute:
    """Tests for code execution."""

    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client with container support."""
        client = MagicMock()
        client.ping.return_value = True

        # Mock container
        container = MagicMock()
        container.id = "test-container-id"
        container.wait.return_value = {"StatusCode": 0}
        container.logs.side_effect = [
            b"Hello, World!\n",  # stdout
            b"",  # stderr
        ]

        client.containers.create.return_value = container
        return client

    @pytest.mark.asyncio
    async def test_execute_code_unsupported_language(self, mock_docker_client):
        """Test execution with unsupported language."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager
            from maios.sandbox.models import ExecutionRequest

            manager = SandboxManager()
            request = ExecutionRequest(language="ruby", code="puts 'hello'")

            result = await manager.execute_code(request)

            assert result.exit_code == 1
            assert "Unsupported language" in result.error

    @pytest.mark.asyncio
    async def test_execute_code_empty_code(self, mock_docker_client):
        """Test execution with empty code."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager
            from maios.sandbox.models import ExecutionRequest

            manager = SandboxManager()
            request = ExecutionRequest(language="python", code="")

            result = await manager.execute_code(request)

            assert result.exit_code == 1
            assert "No code provided" in result.error

    @pytest.mark.asyncio
    async def test_execute_code_success(self, mock_docker_client):
        """Test successful code execution."""
        with patch("docker.from_env", return_value=mock_docker_client):
            from maios.sandbox.manager import SandboxManager
            from maios.sandbox.models import ExecutionRequest

            manager = SandboxManager()
            request = ExecutionRequest(language="python", code="print('hello')")

            result = await manager.execute_code(request)

            assert result.exit_code == 0
            assert "Hello, World!" in result.stdout
            assert result.duration_ms >= 0  # Duration in ms (can be 0 for fast tests)

            # Verify container was created with correct settings
            mock_docker_client.containers.create.assert_called_once()
            call_kwargs = mock_docker_client.containers.create.call_args[1]
            assert call_kwargs["network_disabled"] is True

    @pytest.mark.asyncio
    async def test_execute_code_failure(self):
        """Test code execution with non-zero exit code."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        container = MagicMock()
        container.id = "test-container-id"
        container.wait.return_value = {"StatusCode": 1}
        container.logs.side_effect = [
            b"",  # stdout
            b"Error: something went wrong\n",  # stderr
        ]

        mock_client.containers.create.return_value = container

        with patch("docker.from_env", return_value=mock_client):
            from maios.sandbox.manager import SandboxManager
            from maios.sandbox.models import ExecutionRequest

            manager = SandboxManager()
            request = ExecutionRequest(language="python", code="raise Exception('error')")

            result = await manager.execute_code(request)

            assert result.exit_code == 1
            assert "Error" in result.stderr


class TestGlobalSandboxManager:
    """Tests for global sandbox manager instance."""

    def test_global_sandbox_manager_exists(self):
        """Test that global sandbox manager exists."""
        from maios.sandbox import sandbox_manager

        assert sandbox_manager is not None
        assert hasattr(sandbox_manager, "execute_code")
        assert hasattr(sandbox_manager, "is_healthy")

    def test_sandbox_manager_imports(self):
        """Test that all expected exports are available."""
        from maios.sandbox import (
            SandboxManager,
            sandbox_manager,
            ContainerMetrics,
            ContainerType,
            ExecutionRequest,
            ExecutionResult,
        )

        assert SandboxManager is not None
        assert sandbox_manager is not None
        assert ContainerMetrics is not None
        assert ContainerType is not None
        assert ExecutionRequest is not None
        assert ExecutionResult is not None
