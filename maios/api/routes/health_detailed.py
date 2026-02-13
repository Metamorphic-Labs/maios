"""Detailed health API routes for MAIOS."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from maios.core.database import async_session, engine
from maios.sandbox import sandbox_manager

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/status")
async def system_health() -> dict[str, Any]:
    """Get overall system health status.

    Returns health status of all major components:
    - Database connectivity
    - Docker sandbox availability
    """
    # Check database
    database_healthy = False
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        database_healthy = True
    except Exception as e:
        pass

    # Check Docker
    docker_healthy = sandbox_manager.is_healthy()

    # Determine overall status
    if database_healthy:
        overall_status = "healthy" if docker_healthy else "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": {
                "status": "healthy" if database_healthy else "unhealthy",
                "type": "postgresql",
            },
            "docker": {
                "status": "healthy" if docker_healthy else "unavailable",
                "type": "sandbox",
            },
        },
    }


@router.get("/tasks")
async def task_health() -> dict[str, Any]:
    """Get task health summary.

    Returns counts of tasks by status.
    """
    from maios.models.task import Task, TaskStatus

    async with async_session() as session:
        # Count by status
        result = await session.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        status_counts = {str(row[0].value): row[1] for row in result.all()}

        # Get active task count
        active_result = await session.execute(
            select(func.count(Task.id)).where(
                Task.status.in_([
                    TaskStatus.PENDING,
                    TaskStatus.ASSIGNED,
                    TaskStatus.IN_PROGRESS,
                ])
            )
        )
        active_count = active_result.scalar() or 0

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "by_status": status_counts,
            "total": sum(status_counts.values()),
            "active": active_count,
        }


@router.get("/agents")
async def agent_health() -> dict[str, Any]:
    """Get agent health summary.

    Returns counts of agents by status and health metrics.
    """
    from maios.models.agent import Agent, AgentStatus

    async with async_session() as session:
        # Count by status
        result = await session.execute(
            select(Agent.status, func.count(Agent.id))
            .where(Agent.is_active == True)
            .group_by(Agent.status)
        )
        status_counts = {str(row[0].value): row[1] for row in result.all()}

        # Get working agents
        working_result = await session.execute(
            select(func.count(Agent.id)).where(
                Agent.is_active == True,
                Agent.status == AgentStatus.WORKING,
            )
        )
        working_count = working_result.scalar() or 0

        # Get total active
        total_result = await session.execute(
            select(func.count(Agent.id)).where(Agent.is_active == True)
        )
        total_active = total_result.scalar() or 0

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "by_status": status_counts,
            "total": total_active,
            "working": working_count,
        }


@router.get("/containers")
async def container_health() -> dict[str, Any]:
    """Get sandbox container health.

    Returns information about active sandbox containers.
    """
    try:
        containers = sandbox_manager.list_active_containers()
        docker_healthy = sandbox_manager.is_healthy()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "docker_available": docker_healthy,
            "active_containers": len(containers),
            "containers": containers,
        }
    except Exception as e:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "docker_available": False,
            "error": str(e),
            "active_containers": 0,
            "containers": [],
        }


@router.get("/metrics")
async def system_metrics() -> dict[str, Any]:
    """Get aggregated system metrics.

    Returns combined metrics for tasks, agents, and system.
    """
    from maios.models.agent import Agent
    from maios.models.task import Task, TaskStatus

    async with async_session() as session:
        # Task metrics
        task_result = await session.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        task_counts = {str(row[0].value): row[1] for row in task_result.all()}

        # Agent metrics
        agent_result = await session.execute(
            select(
                func.count(Agent.id).label("total"),
                func.sum(Agent.tasks_completed).label("completed"),
                func.sum(Agent.tasks_failed).label("failed"),
            ).where(Agent.is_active == True)
        )
        agent_row = agent_result.one()
        agent_total = agent_row.total or 0
        tasks_completed = agent_row.completed or 0
        tasks_failed = agent_row.failed or 0

        # Calculate success rate
        total_tasks = tasks_completed + tasks_failed
        success_rate = round(tasks_completed / max(total_tasks, 1) * 100, 1)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tasks": {
                "by_status": task_counts,
                "total": sum(task_counts.values()),
            },
            "agents": {
                "total": agent_total,
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "success_rate": success_rate,
            },
            "system": {
                "docker_available": sandbox_manager.is_healthy(),
            },
        }
