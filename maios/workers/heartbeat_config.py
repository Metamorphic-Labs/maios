"""Configuration for the heartbeat system."""

from pydantic import BaseModel, Field

from maios.core.config import settings


class HeartbeatConfig(BaseModel):
    """Configuration for the heartbeat monitoring system.

    This model provides a structured way to access heartbeat configuration
    with validation and documentation.

    Attributes:
        interval_minutes: How often heartbeat checks run (in minutes)
        task_stalled_threshold: Minutes without update before task is considered stalled
        task_long_running_threshold: Minutes before task is flagged as long-running
        agent_silent_threshold: Minutes without heartbeat before agent is considered silent
        agent_high_error_rate: Error rate threshold (0.0-1.0) for high error rate alert
    """

    interval_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="How often heartbeat checks run (in minutes)",
    )
    task_stalled_threshold: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Minutes without update before task is considered stalled",
    )
    task_long_running_threshold: int = Field(
        default=120,
        ge=10,
        le=4320,
        description="Minutes before task is flagged as long-running",
    )
    agent_silent_threshold: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="Minutes without heartbeat before agent is considered silent",
    )
    agent_high_error_rate: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Error rate threshold for high error rate alert",
    )

    @classmethod
    def from_settings(cls) -> "HeartbeatConfig":
        """Create HeartbeatConfig from application settings.

        Returns:
            HeartbeatConfig with values from settings
        """
        return cls(
            interval_minutes=settings.heartbeat_interval_minutes,
            task_stalled_threshold=settings.task_stalled_threshold_minutes,
            task_long_running_threshold=settings.task_long_running_threshold_minutes,
            agent_silent_threshold=settings.agent_silent_threshold_minutes,
            agent_high_error_rate=settings.agent_high_error_rate,
        )


# Global config instance (created from settings)
heartbeat_config = HeartbeatConfig.from_settings()
