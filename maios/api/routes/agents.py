# maios/api/routes/agents.py
"""Agents API routes for MAIOS."""

import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from maios.core.database import get_session
from maios.models.agent import Agent, AgentStatus
from maios.models.schemas import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Create a new agent."""
    agent = Agent(
        name=agent_data.name,
        role=agent_data.role,
        persona=agent_data.persona,
        model_provider=agent_data.model_provider,
        model_name=agent_data.model_name,
        goals=agent_data.goals,
        skill_tags=agent_data.skill_tags,
        permissions=agent_data.permissions,
        system_prompt=agent_data.system_prompt,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentRead])
async def list_agents(
    status: Optional[AgentStatus] = Query(None, description="Filter by agent status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_session),
) -> list[Agent]:
    """List all agents with optional filtering and pagination."""
    query = select(Agent)

    if status is not None:
        query = query.where(Agent.status == status)

    query = query.offset(skip).limit(limit).order_by(Agent.created_at.desc())

    result = await session.execute(query)
    agents = result.scalars().all()
    return list(agents)


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Get a specific agent by ID."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    session: AsyncSession = Depends(get_session),
) -> Agent:
    """Update an agent."""
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    agent.updated_at = datetime.datetime.utcnow()
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent
