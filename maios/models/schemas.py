# maios/models/schemas.py
"""Pydantic schemas for the MAIOS API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from maios.models.project import ProjectStatus


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
