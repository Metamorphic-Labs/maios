"""Heartbeat system for monitoring task and agent health."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from celery import shared_task
from sqlalchemy import func, select

from maios.core.config import settings
from maios.workers.heartbeat_config import heartbeat_config

logger = logging.getLogger(__name__)

# Get thresholds from config
TASK_STALLED_THRESHOLD_MINUTES = heartbeat_config.task_stalled_threshold
TASK_LONG_RUNNING_THRESHOLD_MINUTES = heartbeat_config.task_long_running_threshold
AGENT_SILENT_THRESHOLD_MINUTES = heartbeat_config.agent_silent_threshold
HIGH_ERROR_RATE_THRESHOLD = heartbeat_config.agent_high_error_rate


async def get_active_tasks():
    """Get all active (non-completed) tasks from database."""
    from maios.core.database import async_session
    from maios.models.task import Task, TaskStatus

    async with async_session() as session:
        result = await session.execute(
            select(Task).where(
                Task.status.in_([
                    TaskStatus.PENDING,
                    TaskStatus.ASSIGNED,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.BLOCKED,
                ])
            )
        )
        return list(result.scalars().all())


async def get_active_agents():
    """Get all active agents from database."""
    from maios.core.database import async_session
    from maios.models.agent import Agent

    async with async_session() as session:
        result = await session.execute(
            select(Agent).where(Agent.is_active == True)
        )
        return list(result.scalars().all())


async def dispatch_action(action: str, **kwargs) -> dict[str, Any]:
    """Dispatch an action based on health check results.

    This function handles various health-related actions:
    - Logs the action
    - In a full implementation, would send notifications
    - Could trigger auto-remediation

    Args:
        action: Type of action (task_stalled, agent_silent, etc.)
        **kwargs: Additional context for the action

    Returns:
        dict with action result
    """
    severity = kwargs.get("severity", "info")

    # Log the action
    log_msg = f"Health action: {action} (severity: {severity})"
    if severity == "critical":
        logger.critical(log_msg)
    elif severity == "warning":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    # Log additional context
    for key, value in kwargs.items():
        if key != "severity":
            logger.info(f"  {key}: {value}")

    # Return action record
    return {
        "action": action,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": kwargs,
    }


async def check_task_health() -> list[dict[str, Any]]:
    """Check health of all active tasks.

    Identifies:
    - Stalled tasks (no update for too long)
    - Long-running tasks (exceeded expected duration)

    Returns:
        List of actions dispatched
    """
    now = datetime.now(timezone.utc)
    actions = []

    tasks = await get_active_tasks()
    logger.info(f"Checking health of {len(tasks)} active tasks")

    for task in tasks:
        # Ensure timezone-aware datetime
        last_updated = task.updated_at
        if last_updated and last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        if not last_updated:
            continue

        time_since_update = (now - last_updated).total_seconds() / 60

        # Check if task is stalled
        if time_since_update > TASK_STALLED_THRESHOLD_MINUTES:
            action = await dispatch_action(
                action="task_stalled",
                task_id=str(task.id),
                task_title=task.title,
                severity="warning",
                minutes_stalled=int(time_since_update),
                status=task.status.value if hasattr(task.status, "value") else str(task.status),
            )
            actions.append(action)

        # Check if task is running too long
        if task.started_at:
            started_at = task.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)

            time_since_start = (now - started_at).total_seconds() / 60

            if time_since_start > TASK_LONG_RUNNING_THRESHOLD_MINUTES:
                action = await dispatch_action(
                    action="task_long_running",
                    task_id=str(task.id),
                    task_title=task.title,
                    severity="info",
                    minutes_running=int(time_since_start),
                    timeout_minutes=task.timeout_minutes,
                )
                actions.append(action)

    return actions


async def check_agent_health() -> list[dict[str, Any]]:
    """Check health of all active agents.

    Identifies:
    - Silent agents (no heartbeat for too long)
    - High error rate agents

    Returns:
        List of actions dispatched
    """
    now = datetime.now(timezone.utc)
    actions = []

    agents = await get_active_agents()
    logger.info(f"Checking health of {len(agents)} active agents")

    for agent in agents:
        # Check if agent is silent (no heartbeat)
        if agent.last_heartbeat:
            last_heartbeat = agent.last_heartbeat
            if last_heartbeat.tzinfo is None:
                last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)

            time_since_heartbeat = (now - last_heartbeat).total_seconds() / 60

            if time_since_heartbeat > AGENT_SILENT_THRESHOLD_MINUTES:
                action = await dispatch_action(
                    action="agent_silent",
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    severity="warning",
                    minutes_silent=int(time_since_heartbeat),
                    status=agent.status.value if hasattr(agent.status, "value") else str(agent.status),
                )
                actions.append(action)

        # Check error rate
        total_tasks = agent.tasks_completed + agent.tasks_failed
        if total_tasks > 0:
            error_rate = agent.tasks_failed / total_tasks
            if error_rate > HIGH_ERROR_RATE_THRESHOLD:
                action = await dispatch_action(
                    action="agent_high_errors",
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    severity="warning",
                    error_rate=round(error_rate, 2),
                    tasks_completed=agent.tasks_completed,
                    tasks_failed=agent.tasks_failed,
                )
                actions.append(action)

    return actions


async def run_all_health_checks() -> dict[str, Any]:
    """Run all health checks and return summary.

    Returns:
        dict with health check results
    """
    start_time = datetime.now(timezone.utc)

    # Run checks in parallel
    task_actions, agent_actions = await asyncio.gather(
        check_task_health(),
        check_agent_health(),
        return_exceptions=True,
    )

    # Handle exceptions
    if isinstance(task_actions, Exception):
        logger.error(f"Task health check failed: {task_actions}")
        task_actions = []

    if isinstance(agent_actions, Exception):
        logger.error(f"Agent health check failed: {agent_actions}")
        agent_actions = []

    end_time = datetime.now(timezone.utc)
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    result = {
        "status": "completed",
        "timestamp": start_time.isoformat(),
        "duration_ms": duration_ms,
        "task_actions": len(task_actions),
        "agent_actions": len(agent_actions),
        "actions": task_actions + agent_actions,
    }

    logger.info(f"Health checks completed: {result['task_actions']} task issues, {result['agent_actions']} agent issues")

    return result


@shared_task(name="maios.workers.heartbeat.run_health_checks")
def run_health_checks_task():
    """Celery task to run all health checks.

    This task is scheduled by Celery Beat to run periodically.
    """
    logger.info("Starting health check task...")

    result = asyncio.run(run_all_health_checks())

    logger.info(f"Health check task completed: {result['status']}")
    return result


@shared_task(name="maios.workers.heartbeat.generate_daily_summary")
def generate_daily_summary():
    """Generate daily performance summary.

    Collects statistics on agents and tasks for the daily report.
    """
    import asyncio

    async def _generate():
        from maios.core.database import async_session
        from maios.models.agent import Agent
        from maios.models.task import Task, TaskStatus

        async with async_session() as session:
            # Get agent stats
            agent_result = await session.execute(
                select(Agent)
                .where(Agent.is_active == True)
                .order_by(Agent.performance_score.desc())
            )
            agents = list(agent_result.scalars().all())

            # Get task stats
            total_result = await session.execute(
                select(func.count()).select_from(Task)
            )
            total_tasks = total_result.scalar() or 0

            completed_result = await session.execute(
                select(func.count()).select_from(Task).where(Task.status == TaskStatus.COMPLETED)
            )
            completed_tasks = completed_result.scalar() or 0

            failed_result = await session.execute(
                select(func.count()).select_from(Task).where(Task.status == TaskStatus.FAILED)
            )
            failed_tasks = failed_result.scalar() or 0

            # Build summary
            summary = {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "agents": {
                    "total": len(agents),
                    "top_performers": [
                        {
                            "name": a.name,
                            "role": a.role,
                            "score": a.performance_score,
                            "tasks_completed": a.tasks_completed,
                        }
                        for a in agents[:5]
                    ],
                },
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "failed": failed_tasks,
                    "success_rate": round(completed_tasks / max(total_tasks, 1) * 100, 1),
                },
            }

            logger.info(f"Daily summary generated: {summary}")
            return summary

    return asyncio.run(_generate())
