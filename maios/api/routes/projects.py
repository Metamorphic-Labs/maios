# maios/api/routes/projects.py
"""Projects API routes for MAIOS."""

import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from maios.core.database import get_session
from maios.models.project import Project, ProjectStatus
from maios.models.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Create a new project."""
    project = Project(
        name=project_data.name,
        description=project_data.description,
        initial_request=project_data.initial_request,
        tech_stack=project_data.tech_stack,
        constraints=project_data.constraints,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    status: Optional[ProjectStatus] = Query(None, description="Filter by project status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    """List all projects with optional filtering and pagination."""
    query = select(Project)

    if status is not None:
        query = query.where(Project.status == status)

    query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())

    result = await session.execute(query)
    projects = result.scalars().all()
    return list(projects)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Get a specific project by ID."""
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    """Update a project."""
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.datetime.utcnow()
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project
