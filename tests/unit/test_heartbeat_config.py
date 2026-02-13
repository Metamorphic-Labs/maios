"""Tests for Heartbeat Configuration."""

import pytest
from unittest.mock import patch


class TestHeartbeatConfig:
    """Tests for HeartbeatConfig model."""

    def test_heartbeat_config_defaults(self):
        """Test HeartbeatConfig has correct defaults."""
        from maios.workers.heartbeat_config import HeartbeatConfig

        config = HeartbeatConfig()

        assert config.interval_minutes == 5
        assert config.task_stalled_threshold == 30
        assert config.task_long_running_threshold == 120
        assert config.agent_silent_threshold == 15
        assert config.agent_high_error_rate == 0.3

    def test_heartbeat_config_validation(self):
        """Test HeartbeatConfig validates inputs."""
        from maios.workers.heartbeat_config import HeartbeatConfig
        from pydantic import ValidationError

        # Valid config
        config = HeartbeatConfig(
            interval_minutes=10,
            task_stalled_threshold=60,
            task_long_running_threshold=240,
            agent_silent_threshold=30,
            agent_high_error_rate=0.5,
        )
        assert config.interval_minutes == 10

        # Invalid: interval too low
        with pytest.raises(ValidationError):
            HeartbeatConfig(interval_minutes=0)

        # Invalid: interval too high
        with pytest.raises(ValidationError):
            HeartbeatConfig(interval_minutes=100)

        # Invalid: error rate too high
        with pytest.raises(ValidationError):
            HeartbeatConfig(agent_high_error_rate=1.5)

    def test_heartbeat_config_from_settings(self):
        """Test HeartbeatConfig.from_settings creates config from settings."""
        from maios.workers.heartbeat_config import HeartbeatConfig

        with patch("maios.workers.heartbeat_config.settings") as mock_settings:
            mock_settings.heartbeat_interval_minutes = 10
            mock_settings.task_stalled_threshold_minutes = 60
            mock_settings.task_long_running_threshold_minutes = 180
            mock_settings.agent_silent_threshold_minutes = 20
            mock_settings.agent_high_error_rate = 0.4

            config = HeartbeatConfig.from_settings()

            assert config.interval_minutes == 10
            assert config.task_stalled_threshold == 60
            assert config.task_long_running_threshold == 180
            assert config.agent_silent_threshold == 20
            assert config.agent_high_error_rate == 0.4

    def test_global_heartbeat_config_exists(self):
        """Test that global heartbeat_config instance exists."""
        from maios.workers.heartbeat_config import heartbeat_config

        assert heartbeat_config is not None
        assert hasattr(heartbeat_config, "interval_minutes")
        assert hasattr(heartbeat_config, "task_stalled_threshold")


class TestHeartbeatUsesConfig:
    """Tests that heartbeat module uses configuration."""

    def test_heartbeat_imports_config(self):
        """Test that heartbeat module imports configuration."""
        from maios.workers import heartbeat

        assert hasattr(heartbeat, "heartbeat_config")
        assert hasattr(heartbeat, "TASK_STALLED_THRESHOLD_MINUTES")

    def test_thresholds_match_config(self):
        """Test that thresholds in heartbeat match config."""
        from maios.workers import heartbeat
        from maios.workers.heartbeat_config import heartbeat_config

        assert heartbeat.TASK_STALLED_THRESHOLD_MINUTES == heartbeat_config.task_stalled_threshold
        assert heartbeat.TASK_LONG_RUNNING_THRESHOLD_MINUTES == heartbeat_config.task_long_running_threshold
        assert heartbeat.AGENT_SILENT_THRESHOLD_MINUTES == heartbeat_config.agent_silent_threshold
        assert heartbeat.HIGH_ERROR_RATE_THRESHOLD == heartbeat_config.agent_high_error_rate


class TestCeleryBeatUsesConfig:
    """Tests that Celery Beat uses configurable interval."""

    def test_beat_schedule_uses_config_interval(self):
        """Test that beat schedule uses config interval."""
        from maios.workers.celery_app import app
        from maios.workers.heartbeat_config import heartbeat_config

        schedule = app.conf.beat_schedule
        expected_interval = heartbeat_config.interval_minutes * 60.0

        assert schedule["heartbeat-check"]["schedule"] == expected_interval
