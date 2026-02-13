# maios/models/schemas.py
"""Pydantic schemas for the MAIOS API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from maios.models.agent import AgentStatus
from maios.models.project import ProjectStatus


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    name: str
    role: str
    persona: str
    model_provider: str = "z.ai"
    model_name: str = "glm-4-plus"
    goals: list[str] = []
    skill_tags: list[str] = []
    permissions: list[str] = []
    system_prompt: Optional[str] = None


class AgentRead(BaseModel):
    """Schema for reading an agent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    persona: str
    status: AgentStatus
    skill_tags: list[str]
    permissions: list[str]
    performance_score: float
    current_task_id: Optional[UUID]


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = None
    role: Optional[str] = None
    persona: Optional[str] = None
    status: Optional[AgentStatus] = None
    system_prompt: Optional[str] = None


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str
    description: Optional[str] = None
    initial_request: Optional[str] = None
    tech_stack: list[str] = []
    constraints: dict = {}


class ProjectRead(BaseModel):
    """Schema for reading a project."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    description: Optional[str]
    status: ProjectStatus
    initial_request: Optional[str]
    tech_stack: list[str]
    orchestrator_phase: str


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
