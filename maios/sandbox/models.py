"""Sandbox models for MAIOS."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContainerType(str, Enum):
    """Type of sandbox container."""

    EXECUTION = "execution"  # Run code snippets
    TEST_RUNNER = "test_runner"  # Run tests
    PREVIEW = "preview"  # Serve application


class ContainerStatus(str, Enum):
    """Status of a sandbox container."""

    CREATING = "creating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


class ExecutionRequest(BaseModel):
    """Request to execute code in sandbox."""

    language: str  # python, javascript, typescript
    code: str
    context_files: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ExecutionResult(BaseModel):
    """Result of code execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    memory_used_mb: float = 0.0
    error: Optional[str] = None

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.error


class TestExecutionRequest(BaseModel):
    """Request to run tests in sandbox."""

    project_path: str
    test_command: str
    environment: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=1800)


class TestExecutionResult(BaseModel):
    """Result of test execution."""

    passed: int
    failed: int
    skipped: int
    output: str
    duration_ms: int
    failures: list[dict[str, Any]] = Field(default_factory=list)
    coverage: Optional[float] = None
    error: Optional[str] = None


class PreviewRequest(BaseModel):
    """Request to start a preview container."""

    project_path: str
    command: str
    port: int = Field(default=3000, ge=1, le=65535)
    environment: dict[str, str] = Field(default_factory=dict)


class PreviewResult(BaseModel):
    """Result of preview container start."""

    container_id: str
    url: str
    status: ContainerStatus
    logs: str
    error: Optional[str] = None


class ContainerMetrics(BaseModel):
    """Metrics for a running container."""

    container_id: str
    cpu_percent: float
    memory_mb: float
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    uptime_seconds: int = 0

    @classmethod
    def from_docker_stats(cls, container_id: str, stats: dict) -> "ContainerMetrics":
        """Create metrics from Docker stats response."""
        cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        cpu_system = stats.get("cpu_stats", {}).get("system_cpu_usage", 1)
        pre_cpu_delta = stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        pre_cpu_system = stats.get("precpu_stats", {}).get("system_cpu_usage", 1)

        cpu_percent = 0.0
        if cpu_system > pre_cpu_system and cpu_delta > pre_cpu_delta:
            cpu_percent = ((cpu_delta - pre_cpu_delta) / (cpu_system - pre_cpu_system)) * 100

        memory_stats = stats.get("memory_stats", {})
        memory_mb = memory_stats.get("usage", 0) / (1024 * 1024)

        networks = stats.get("networks", {})
        rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
        tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())

        return cls(
            container_id=container_id,
            cpu_percent=round(cpu_percent, 2),
            memory_mb=round(memory_mb, 2),
            network_rx_bytes=rx_bytes,
            network_tx_bytes=tx_bytes,
        )
