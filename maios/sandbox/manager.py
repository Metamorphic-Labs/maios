"""Sandbox manager for Docker-based code execution."""

import asyncio
import logging
import time
from typing import Optional

from docker import errors as docker_errors

from maios.sandbox.models import (
    ContainerType,
    ContainerMetrics,
    ExecutionRequest,
    ExecutionResult,
    PreviewRequest,
    PreviewResult,
    TestExecutionRequest,
    TestExecutionResult,
)

logger = logging.getLogger(__name__)

# Container image mappings
CONTAINER_IMAGES = {
    "python": "python:3.12-slim",
    "javascript": "node:20-slim",
    "typescript": "node:20-slim",
}

# Resource limits by container type
RESOURCE_LIMITS = {
    ContainerType.EXECUTION: {
        "mem_limit": "512m",
        "cpu_period": 100000,
        "cpu_quota": 100000,  # 1 CPU
        "pids_limit": 100,
    },
    ContainerType.TEST_RUNNER: {
        "mem_limit": "2g",
        "cpu_period": 100000,
        "cpu_quota": 200000,  # 2 CPUs
        "pids_limit": 200,
    },
    ContainerType.PREVIEW: {
        "mem_limit": "1g",
        "cpu_period": 100000,
        "cpu_quota": 100000,
        "pids_limit": 150,
    },
}


class SandboxManager:
    """Manages Docker-based sandbox containers for code execution."""

    def __init__(self):
        self._client = None
        self._active_containers: dict[str, dict] = {}

    @property
    def client(self):
        """Lazy-loaded Docker client."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
                logger.info("Docker client initialized successfully")
            except docker_errors.DockerException as e:
                logger.error(f"Failed to connect to Docker daemon: {e}")
                raise
        return self._client

    def is_healthy(self) -> bool:
        """Check if Docker daemon is accessible."""
        try:
            self.client.ping()
            return True
        except (docker_errors.DockerException, Exception):
            return False

    def _get_image(self, language: str) -> Optional[str]:
        """Get Docker image for a language."""
        return CONTAINER_IMAGES.get(language)

    def _build_command(self, language: str, code: str) -> list[str]:
        """Build container command for code execution."""
        if language == "python":
            return ["python", "-c", code]
        elif language in ("javascript", "typescript"):
            return ["node", "-e", code]
        else:
            raise ValueError(f"Unsupported language: {language}")

    async def execute_code(
        self,
        request: ExecutionRequest,
        container_type: ContainerType = ContainerType.EXECUTION,
    ) -> ExecutionResult:
        """Execute code in a sandbox container.

        Args:
            request: Execution request with code and language
            container_type: Type of container (affects resource limits)

        Returns:
            ExecutionResult with stdout, stderr, and exit code
        """
        start_time = time.monotonic()
        container = None

        try:
            # Validate language
            image = self._get_image(request.language)
            if not image:
                return ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="",
                    duration_ms=0,
                    error=f"Unsupported language: {request.language}. Supported: {list(CONTAINER_IMAGES.keys())}",
                )

            # Validate code
            if not request.code or not request.code.strip():
                return ExecutionResult(
                    exit_code=1,
                    stdout="",
                    stderr="",
                    duration_ms=0,
                    error="No code provided",
                )

            # Build command
            command = self._build_command(request.language, request.code)

            # Get resource limits
            limits = RESOURCE_LIMITS[container_type]

            # Create container
            container = self.client.containers.create(
                image=image,
                command=command,
                mem_limit=limits["mem_limit"],
                cpu_period=limits["cpu_period"],
                cpu_quota=limits["cpu_quota"],
                pids_limit=limits["pids_limit"],
                network_disabled=True,  # No network access for security
                detach=True,
                labels={
                    "maios.type": "sandbox",
                    "maios.container_type": container_type.value,
                },
            )

            logger.info(f"Created container {container.id[:12]} for {request.language} execution")

            # Start container
            container.start()

            # Wait for completion with timeout
            try:
                result = container.wait(timeout=request.timeout_seconds)
                exit_code = result.get("StatusCode", 1)
            except Exception as e:
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    container.kill()
                    return ExecutionResult(
                        exit_code=137,  # SIGKILL
                        stdout="",
                        stderr="",
                        duration_ms=request.timeout_seconds * 1000,
                        error=f"Execution timed out after {request.timeout_seconds} seconds",
                    )
                raise

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(f"Container {container.id[:12]} completed with exit code {exit_code}")

            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
            )

        except docker_errors.ImageNotFound as e:
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="",
                duration_ms=int((time.monotonic() - start_time) * 1000),
                error=f"Docker image not found: {e}",
            )

        except docker_errors.APIError as e:
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="",
                duration_ms=int((time.monotonic() - start_time) * 1000),
                error=f"Docker API error: {e}",
            )

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="",
                duration_ms=int((time.monotonic() - start_time) * 1000),
                error=str(e),
            )

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                    logger.debug(f"Removed container {container.id[:12]}")
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

    async def run_tests(self, request: TestExecutionRequest) -> TestExecutionResult:
        """Run tests in a sandbox container.

        Note: This is a placeholder - full implementation requires project mounting.
        """
        return TestExecutionResult(
            passed=0,
            failed=0,
            skipped=0,
            output="",
            duration_ms=0,
            error="Test execution requires project directory mounting (not yet implemented)",
        )

    async def start_preview(self, request: PreviewRequest) -> PreviewResult:
        """Start a preview container.

        Note: This is a placeholder - full implementation requires project mounting.
        """
        return PreviewResult(
            container_id="",
            url="",
            status="failed",
            logs="",
            error="Preview mode requires project directory mounting (not yet implemented)",
        )

    async def stop_preview(self, container_id: str) -> bool:
        """Stop a preview container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            return False

    def get_metrics(self, container_id: str) -> Optional[ContainerMetrics]:
        """Get metrics for a running container."""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            return ContainerMetrics.from_docker_stats(container_id, stats)
        except Exception as e:
            logger.error(f"Failed to get metrics for {container_id}: {e}")
            return None

    def list_active_containers(self) -> list[dict]:
        """List all MAIOS sandbox containers."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "maios.type=sandbox"},
            )
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else c.image.id,
                    "labels": c.labels,
                }
                for c in containers
            ]
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def cleanup_all(self) -> int:
        """Remove all MAIOS sandbox containers."""
        count = 0
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "maios.type=sandbox"},
            )
            for container in containers:
                try:
                    container.remove(force=True)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove container {container.id}: {e}")
        except Exception as e:
            logger.error(f"Failed to cleanup containers: {e}")
        return count


# Global sandbox manager instance
sandbox_manager = SandboxManager()
