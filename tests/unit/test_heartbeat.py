"""Tests for Heartbeat system."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestHeartbeatFunctions:
    """Tests for heartbeat utility functions."""

    @pytest.mark.asyncio
    async def test_dispatch_action_logs_info(self):
        """Test dispatch_action logs info level."""
        from maios.workers.heartbeat import dispatch_action

        with patch("maios.workers.heartbeat.logger") as mock_logger:
            result = await dispatch_action(
                action="test_action",
                severity="info",
                test_key="test_value",
            )

        assert result["action"] == "test_action"
        assert result["severity"] == "info"
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_dispatch_action_logs_warning(self):
        """Test dispatch_action logs warning level."""
        from maios.workers.heartbeat import dispatch_action

        with patch("maios.workers.heartbeat.logger") as mock_logger:
            result = await dispatch_action(
                action="test_warning",
                severity="warning",
            )

        assert result["severity"] == "warning"
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_dispatch_action_logs_critical(self):
        """Test dispatch_action logs critical level."""
        from maios.workers.heartbeat import dispatch_action

        with patch("maios.workers.heartbeat.logger") as mock_logger:
            result = await dispatch_action(
                action="test_critical",
                severity="critical",
            )

        assert result["severity"] == "critical"
        mock_logger.critical.assert_called()


class TestTaskHealthCheck:
    """Tests for task health checks."""

    @pytest.mark.asyncio
    async def test_check_task_health_no_tasks(self):
        """Test check_task_health with no active tasks."""
        with patch("maios.workers.heartbeat.get_active_tasks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            from maios.workers.heartbeat import check_task_health

            actions = await check_task_health()

            assert actions == []

    @pytest.mark.asyncio
    async def test_check_task_health_detects_stalled(self):
        """Test check_task_health detects stalled tasks."""
        from maios.workers.heartbeat import check_task_health
        from maios.models.task import Task, TaskStatus

        # Create a stalled task
        stalled_task = MagicMock(spec=Task)
        stalled_task.id = "test-id"
        stalled_task.title = "Stalled Task"
        stalled_task.status = TaskStatus.IN_PROGRESS
        stalled_task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        stalled_task.started_at = None

        with patch("maios.workers.heartbeat.get_active_tasks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [stalled_task]

            actions = await check_task_health()

        # Should detect stalled task
        assert len(actions) >= 1
        assert any(a["action"] == "task_stalled" for a in actions)

    @pytest.mark.asyncio
    async def test_check_task_health_detects_long_running(self):
        """Test check_task_health detects long-running tasks."""
        from maios.workers.heartbeat import check_task_health
        from maios.models.task import Task, TaskStatus

        # Create a long-running task
        long_task = MagicMock(spec=Task)
        long_task.id = "test-id"
        long_task.title = "Long Task"
        long_task.status = TaskStatus.IN_PROGRESS
        long_task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        long_task.started_at = datetime.now(timezone.utc) - timedelta(minutes=150)
        long_task.timeout_minutes = 60

        with patch("maios.workers.heartbeat.get_active_tasks", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [long_task]

            actions = await check_task_health()

        # Should detect long-running task
        assert len(actions) >= 1
        assert any(a["action"] == "task_long_running" for a in actions)


class TestAgentHealthCheck:
    """Tests for agent health checks."""

    @pytest.mark.asyncio
    async def test_check_agent_health_no_agents(self):
        """Test check_agent_health with no active agents."""
        with patch("maios.workers.heartbeat.get_active_agents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            from maios.workers.heartbeat import check_agent_health

            actions = await check_agent_health()

            assert actions == []

    @pytest.mark.asyncio
    async def test_check_agent_health_detects_silent(self):
        """Test check_agent_health detects silent agents."""
        from maios.workers.heartbeat import check_agent_health
        from maios.models.agent import Agent, AgentStatus

        # Create a silent agent
        silent_agent = MagicMock(spec=Agent)
        silent_agent.id = "test-id"
        silent_agent.name = "SilentAgent"
        silent_agent.status = AgentStatus.IDLE
        silent_agent.last_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=30)
        silent_agent.tasks_completed = 10
        silent_agent.tasks_failed = 0

        with patch("maios.workers.heartbeat.get_active_agents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [silent_agent]

            actions = await check_agent_health()

        # Should detect silent agent
        assert len(actions) >= 1
        assert any(a["action"] == "agent_silent" for a in actions)

    @pytest.mark.asyncio
    async def test_check_agent_health_detects_high_errors(self):
        """Test check_agent_health detects high error rate."""
        from maios.workers.heartbeat import check_agent_health
        from maios.models.agent import Agent, AgentStatus

        # Create an agent with high error rate
        error_agent = MagicMock(spec=Agent)
        error_agent.id = "test-id"
        error_agent.name = "ErrorAgent"
        error_agent.status = AgentStatus.IDLE
        error_agent.last_heartbeat = datetime.now(timezone.utc)
        error_agent.tasks_completed = 5
        error_agent.tasks_failed = 10  # 66% error rate

        with patch("maios.workers.heartbeat.get_active_agents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [error_agent]

            actions = await check_agent_health()

        # Should detect high error rate
        assert len(actions) >= 1
        assert any(a["action"] == "agent_high_errors" for a in actions)


class TestRunAllHealthChecks:
    """Tests for run_all_health_checks function."""

    @pytest.mark.asyncio
    async def test_run_all_health_checks(self):
        """Test run_all_health_checks runs both checks."""
        from maios.workers.heartbeat import run_all_health_checks

        with patch("maios.workers.heartbeat.check_task_health", new_callable=AsyncMock) as mock_task:
            with patch("maios.workers.heartbeat.check_agent_health", new_callable=AsyncMock) as mock_agent:
                mock_task.return_value = [{"action": "task_stalled"}]
                mock_agent.return_value = [{"action": "agent_silent"}]

                result = await run_all_health_checks()

        assert result["status"] == "completed"
        assert result["task_actions"] == 1
        assert result["agent_actions"] == 1
        assert len(result["actions"]) == 2

    @pytest.mark.asyncio
    async def test_run_all_health_checks_handles_exceptions(self):
        """Test run_all_health_checks handles exceptions gracefully."""
        from maios.workers.heartbeat import run_all_health_checks

        with patch("maios.workers.heartbeat.check_task_health", new_callable=AsyncMock) as mock_task:
            with patch("maios.workers.heartbeat.check_agent_health", new_callable=AsyncMock) as mock_agent:
                mock_task.side_effect = Exception("Task check failed")
                mock_agent.return_value = []

                result = await run_all_health_checks()

        assert result["status"] == "completed"
        assert result["task_actions"] == 0  # Exception handled
        assert result["agent_actions"] == 0


class TestCeleryTasks:
    """Tests for Celery tasks."""

    def test_run_health_checks_task_registered(self):
        """Test that run_health_checks_task is a Celery task."""
        from maios.workers.heartbeat import run_health_checks_task

        assert hasattr(run_health_checks_task, "delay")
        assert hasattr(run_health_checks_task, "apply_async")

    def test_generate_daily_summary_registered(self):
        """Test that generate_daily_summary is a Celery task."""
        from maios.workers.heartbeat import generate_daily_summary

        assert hasattr(generate_daily_summary, "delay")
        assert hasattr(generate_daily_summary, "apply_async")

    def test_generate_daily_summary_has_correct_name(self):
        """Test that generate_daily_summary has correct task name."""
        from maios.workers.heartbeat import generate_daily_summary

        assert generate_daily_summary.name == "maios.workers.heartbeat.generate_daily_summary"


class TestCeleryBeatSchedule:
    """Tests for Celery Beat schedule configuration."""

    def test_beat_schedule_has_heartbeat_check(self):
        """Test that beat schedule includes heartbeat check."""
        from maios.workers.celery_app import app

        schedule = app.conf.beat_schedule

        assert "heartbeat-check" in schedule
        assert schedule["heartbeat-check"]["task"] == "maios.workers.heartbeat.run_health_checks"
        assert schedule["heartbeat-check"]["schedule"] == 300.0

    def test_beat_schedule_has_daily_summary(self):
        """Test that beat schedule includes daily summary."""
        from maios.workers.celery_app import app

        schedule = app.conf.beat_schedule

        assert "daily-summary" in schedule
        assert schedule["daily-summary"]["task"] == "maios.workers.heartbeat.generate_daily_summary"

    def test_heartbeat_included_in_celery(self):
        """Test that heartbeat module is included in Celery."""
        from maios.workers.celery_app import app

        assert "maios.workers.heartbeat" in app.conf.include
