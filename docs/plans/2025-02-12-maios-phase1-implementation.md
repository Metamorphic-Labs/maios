# MAIOS Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core MAIOS backend: Orchestrator, Agent Engine, Memory System, Skills, and CLI.

**Architecture:** Modular monolith with async workers. FastAPI handles API requests, Celery manages background tasks, LangGraph powers the orchestrator state machine. PostgreSQL with pgvector for persistence, Redis for ephemeral state.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, LangGraph, Z.ai SDK, Celery, PostgreSQL/pgvector, Redis, Docker, Typer

---

## Prerequisites

Before starting:
- Python 3.12+ installed
- Docker and Docker Compose installed
- Z.ai API key available

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `maios/__init__.py`
- Create: `maios/core/__init__.py`
- Create: `maios/models/__init__.py`
- Create: `maios/api/__init__.py`
- Create: `maios/skills/__init__.py`
- Create: `maios/workers/__init__.py`
- Create: `tests/__init__.py`
- Create: `.env.example`

**Step 1: Create project directory structure**

```bash
mkdir -p maios/{core,models,api/routes,skills/builtin,workers,sandbox,cli}
mkdir -p tests/{unit,integration}
mkdir -p migrations
mkdir -p docker
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "maios"
version = "0.1.0"
description = "Metamorphic AI Orchestration System"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlmodel>=0.0.14",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "celery[redis]>=5.3.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "typer>=0.9.0",
    "rich>=13.7.0",
    "httpx>=0.26.0",
    "websockets>=12.0",
    "docker>=7.0.0",
    "langgraph>=0.0.20",
    "zai-sdk>=0.1.0",
    "psycopg2-binary>=2.9.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
]

[project.scripts]
maios = "maios.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Create .env.example**

```bash
# Z.ai Configuration
ZAI_API_KEY=your-api-key-here
DEFAULT_MODEL=glm-4-plus

# Database
DATABASE_URL=postgresql://maios:maios@localhost:5432/maios

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
TASK_TIMEOUT_MINUTES=30
MULTI_TENANT_MODE=false
LOG_LEVEL=INFO
```

**Step 4: Create __init__.py files**

```bash
touch maios/__init__.py
touch maios/core/__init__.py
touch maios/models/__init__.py
touch maios/api/__init__.py
touch maios/api/routes/__init__.py
touch maios/skills/__init__.py
touch maios/skills/builtin/__init__.py
touch maios/workers/__init__.py
touch maios/sandbox/__init__.py
touch maios/cli/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

**Step 5: Commit scaffolding**

```bash
git add .
git commit -m "chore: initialize project structure

- Add pyproject.toml with dependencies
- Create directory structure for maios modules
- Add .env.example for configuration"
```

---

## Task 2: Docker Infrastructure

**Files:**
- Create: `docker-compose.yml`
- Create: `docker/Dockerfile`
- Create: `docker/Dockerfile.worker`

**Step 1: Create docker-compose.yml**

```yaml
version: "3.12"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: maios
      POSTGRES_PASSWORD: maios
      POSTGRES_DB: maios
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U maios"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://maios:maios@postgres:5432/maios
      - REDIS_URL=redis://redis:6379/0
      - ZAI_API_KEY=${ZAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./maios:/app/maios:ro
    command: uvicorn maios.api.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://maios:maios@postgres:5432/maios
      - REDIS_URL=redis://redis:6379/0
      - ZAI_API_KEY=${ZAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./maios:/app/maios:ro
    command: celery -A maios.workers.celery_app worker --loglevel=info

  beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A maios.workers.celery_app beat --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

**Step 2: Create docker/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application
COPY maios/ ./maios/
COPY migrations/ ./migrations/

EXPOSE 8000

CMD ["uvicorn", "maios.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create docker/Dockerfile.worker**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application
COPY maios/ ./maios/

CMD ["celery", "-A", "maios.workers.celery_app", "worker", "--loglevel=info"]
```

**Step 4: Commit Docker infrastructure**

```bash
git add docker/ docker-compose.yml
git commit -m "feat: add Docker infrastructure

- docker-compose.yml with postgres, redis, api, worker, beat
- Dockerfile for API service
- Dockerfile.worker for Celery workers"
```

---

## Task 3: Configuration Module

**Files:**
- Create: `maios/core/config.py`
- Create: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_config.py
import pytest
from pydantic import ValidationError


def test_config_defaults():
    """Test configuration loads with defaults."""
    from maios.core.config import Settings

    settings = Settings(
        zai_api_key="test-key",
        database_url="postgresql://localhost/maios",
        redis_url="redis://localhost/6379/0",
    )

    assert settings.default_model == "glm-4-plus"
    assert settings.task_timeout_minutes == 30
    assert settings.multi_tenant_mode is False
    assert settings.log_level == "INFO"


def test_config_requires_api_key():
    """Test that API key is required."""
    from maios.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/maios",
            redis_url="redis://localhost/6379/0",
        )
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_config.py -v
```
Expected: FAIL with "No module named 'maios'"

**Step 3: Write minimal implementation**

```python
# maios/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Z.ai Configuration
    zai_api_key: str
    default_model: str = "glm-4-plus"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Application
    task_timeout_minutes: int = 30
    multi_tenant_mode: bool = False
    log_level: str = "INFO"

    # Multi-tenancy (cloud mode)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


# Global settings instance
settings = Settings()  # type: ignore
```

**Step 4: Run test to verify it passes**

```bash
export ZAI_API_KEY=test-key
export DATABASE_URL=postgresql://localhost/maios
export REDIS_URL=redis://localhost/6379/0
pytest tests/unit/test_config.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add maios/core/config.py tests/unit/test_config.py
git commit -m "feat: add configuration module

- Settings class with pydantic-settings
- Environment variable loading
- Default values for all settings"
```

---

## Task 4: Database Connection

**Files:**
- Create: `maios/core/database.py`
- Create: `tests/unit/test_database.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_database.py
import pytest


@pytest.mark.asyncio
async def test_database_engine_creation():
    """Test that database engine can be created."""
    from maios.core.database import create_engine, get_session

    engine = create_engine("sqlite+aiosqlite:///:memory:")

    assert engine is not None
    assert engine.dialect.name == "sqlite"


@pytest.mark.asyncio
async def test_session_dependency():
    """Test session dependency yields session."""
    from maios.core.database import get_session
    from sqlalchemy.ext.asyncio import AsyncSession

    # This would be tested with actual async context
    # For now, just verify the function exists
    assert callable(get_session)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_database.py -v
```
Expected: FAIL with "No module named 'maios.core.database'"

**Step 3: Write minimal implementation**

```python
# maios/core/database.py
from collections.abc import AsyncGenerator
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from maios.core.config import settings


def create_engine(database_url: str):
    """Create async database engine."""
    return create_async_engine(
        database_url,
        echo=settings.log_level == "DEBUG",
        poolclass=NullPool,  # Better for async with pgvector
    )


# Create engine from settings
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.log_level == "DEBUG",
    poolclass=NullPool,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=SQLModelAsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
```

**Step 4: Add aiosqlite dependency to pyproject.toml**

Add to dependencies in pyproject.toml:
```toml
"aiosqlite>=0.19.0",
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_database.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/core/database.py tests/unit/test_database.py pyproject.toml
git commit -m "feat: add database connection module

- Async engine creation with asyncpg
- Session dependency for FastAPI
- Database init and close functions"
```

---

## Task 5: Core Data Models

**Files:**
- Create: `maios/models/agent.py`
- Create: `maios/models/task.py`
- Create: `maios/models/project.py`
- Create: `maios/models/memory.py`
- Create: `tests/unit/test_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from uuid import UUID


def test_agent_model_creation():
    """Test Agent model can be created."""
    from maios.models.agent import Agent, AgentStatus

    agent = Agent(
        name="TestAgent",
        role="Developer",
        model_provider="z.ai",
        model_name="glm-4-plus",
        persona="A helpful coding assistant",
        skill_tags=["code", "test"],
        permissions=["file:read", "file:write"],
    )

    assert agent.name == "TestAgent"
    assert agent.status == AgentStatus.IDLE
    assert isinstance(agent.id, UUID)


def test_task_model_creation():
    """Test Task model can be created."""
    from maios.models.task import Task, TaskStatus, TaskPriority

    task = Task(
        title="Implement feature X",
        description="Add new feature for user authentication",
        project_id=UUID("00000000-0000-0000-0000-000000000001"),
        priority=TaskPriority.HIGH,
    )

    assert task.title == "Implement feature X"
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.HIGH


def test_project_model_creation():
    """Test Project model can be created."""
    from maios.models.project import Project, ProjectStatus

    project = Project(
        name="Test Project",
        description="A test project",
    )

    assert project.name == "Test Project"
    assert project.status == ProjectStatus.PLANNING
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_models.py -v
```
Expected: FAIL with "No module named 'maios.models.agent'"

**Step 3: Write Agent model**

```python
# maios/models/agent.py
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    DISABLED = "disabled"


class Agent(SQLModel, table=True):
    """AI Agent that executes tasks."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Identity
    name: str = Field(index=True)
    role: str = Field(index=True)

    # Model Configuration
    model_provider: str = "z.ai"
    model_name: str = "glm-4-plus"

    # Behavior
    persona: str
    goals: list[str] = Field(default_factory=list)

    # Capabilities
    skill_tags: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    # Communication
    communication_access: list[str] = Field(default_factory=list)

    # Prompt Configuration
    system_prompt: Optional[str] = None
    developer_prompt: Optional[str] = None

    # Status
    status: AgentStatus = Field(default=AgentStatus.IDLE)

    # Performance
    performance_score: float = Field(default=0.0)
    tasks_completed: int = Field(default=0)
    tasks_failed: int = Field(default=0)

    # Current work
    current_task_id: Optional[UUID] = Field(default=None, foreign_key="task.id")

    # Memory
    working_memory_limit: int = 10

    # Team membership
    team_id: Optional[UUID] = Field(default=None, foreign_key="team.id")

    # Metadata
    is_active: bool = Field(default=True)
    last_heartbeat: Optional[datetime] = None
```

**Step 4: Write Task model**

```python
# maios/models/task.py
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(SQLModel, table=True):
    """A unit of work to be executed by an agent."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Identity
    title: str
    description: Optional[str] = None

    # Hierarchy
    project_id: UUID = Field(foreign_key="project.id", index=True)
    parent_task_id: Optional[UUID] = Field(default=None, foreign_key="task.id")
    dependencies: list[UUID] = Field(default_factory=list)

    # Assignment
    assigned_agent_id: Optional[UUID] = Field(default=None, foreign_key="agent.id")

    # Status
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)

    # Progress
    progress_percent: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Configuration
    timeout_minutes: int = 30
    max_retries: int = 3
    retry_count: int = 0

    # Results
    result: Optional[str] = None
    error_message: Optional[str] = None

    # Metadata
    skill_requirements: list[str] = Field(default_factory=list)
    complexity: str = "medium"  # low, medium, high
    metadata: dict = Field(default_factory=dict)
```

**Step 5: Write Project model**

```python
# maios/models/project.py
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(SQLModel, table=True):
    """A project containing multiple tasks orchestrated by the system."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Identity
    name: str
    description: Optional[str] = None

    # Status
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)

    # Configuration
    tech_stack: list[str] = Field(default_factory=list)
    constraints: dict = Field(default_factory=dict)

    # Context
    initial_request: Optional[str] = None
    context_files: list[str] = Field(default_factory=list)

    # Orchestrator state
    orchestrator_phase: str = "PLAN"

    # Metadata
    metadata: dict = Field(default_factory=dict)

    # Multi-tenancy (cloud mode)
    organization_id: Optional[UUID] = Field(default=None)
    owner_id: Optional[UUID] = Field(default=None)
```

**Step 6: Write Memory model**

```python
# maios/models/memory.py
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MemoryType(str, enum.Enum):
    EPISODIC = "episodic"      # Events and experiences
    SEMANTIC = "semantic"      # Facts and knowledge
    PROCEDURAL = "procedural"  # Skills and procedures
    WORKING = "working"        # Temporary, task-specific


class MemoryEntry(SQLModel, table=True):
    """A memory entry stored in the knowledge base."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Content
    content: str
    memory_type: MemoryType

    # Association
    agent_id: Optional[UUID] = Field(default=None, foreign_key="agent.id")
    project_id: Optional[UUID] = Field(default=None, foreign_key="project.id")
    task_id: Optional[UUID] = Field(default=None, foreign_key="task.id")
    team_id: Optional[UUID] = Field(default=None, foreign_key="team.id")

    # Vector embedding (pgvector)
    embedding: Optional[list[float]] = Field(default=None)

    # Metadata
    importance: float = Field(default=0.5)  # 0-1 scale
    access_count: int = Field(default=0)
    last_accessed: Optional[datetime] = None

    # Search
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
```

**Step 7: Update models/__init__.py**

```python
# maios/models/__init__.py
from maios.models.agent import Agent, AgentStatus
from maios.models.task import Task, TaskPriority, TaskStatus
from maios.models.project import Project, ProjectStatus
from maios.models.memory import MemoryEntry, MemoryType

__all__ = [
    "Agent",
    "AgentStatus",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "Project",
    "ProjectStatus",
    "MemoryEntry",
    "MemoryType",
]
```

**Step 8: Run test to verify it passes**

```bash
pytest tests/unit/test_models.py -v
```
Expected: PASS

**Step 9: Commit**

```bash
git add maios/models/ tests/unit/test_models.py
git commit -m "feat: add core data models

- Agent model with status, skills, permissions
- Task model with hierarchy, dependencies
- Project model with orchestrator phase
- MemoryEntry model with vector embedding support"
```

---

## Task 6: Redis Connection

**Files:**
- Create: `maios/core/redis.py`
- Create: `tests/unit/test_redis.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_redis.py
import pytest


def test_redis_client_creation():
    """Test Redis client can be created."""
    from maios.core.redis import get_redis_client

    client = get_redis_client()
    assert client is not None


@pytest.mark.asyncio
async def test_redis_ping():
    """Test Redis connection with ping."""
    from maios.core.redis import get_redis_client

    client = get_redis_client()
    # This would need a running Redis instance
    # For unit test, just verify client exists
    assert client.connection_pool is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_redis.py -v
```
Expected: FAIL with "No module named 'maios.core.redis'"

**Step 3: Write minimal implementation**

```python
# maios/core/redis.py
from redis.asyncio import ConnectionPool, Redis

from maios.core.config import settings


# Create connection pool
_pool: ConnectionPool | None = None


def get_redis_client() -> Redis:
    """Get Redis client instance."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return Redis(connection_pool=_pool)


async def close_redis():
    """Close Redis connection pool."""
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_redis.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add maios/core/redis.py tests/unit/test_redis.py
git commit -m "feat: add Redis connection module

- Async Redis client with connection pool
- get_redis_client factory function
- close_redis cleanup function"
```

---

## Task 7: Celery Setup

**Files:**
- Create: `maios/workers/celery_app.py`
- Create: `maios/workers/tasks.py`
- Create: `tests/unit/test_celery.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_celery.py
def test_celery_app_configuration():
    """Test Celery app is configured correctly."""
    from maios.workers.celery_app import app

    assert app is not None
    assert app.main == "maios.workers.celery_app"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_celery.py -v
```
Expected: FAIL with "No module named 'maios.workers.celery_app'"

**Step 3: Write minimal implementation**

```python
# maios/workers/celery_app.py
from celery import Celery

from maios.core.config import settings

app = Celery(
    "maios",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "maios.workers.tasks",
    ],
)

# Configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule will be added later for heartbeat
app.conf.beat_schedule = {}
```

```python
# maios/workers/tasks.py
from maios.workers.celery_app import app


@app.task(bind=True)
def execute_task(self, task_id: str):
    """Execute a task (placeholder for now)."""
    # Will be implemented in Task 12
    return {"task_id": task_id, "status": "pending"}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_celery.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add maios/workers/ tests/unit/test_celery.py
git commit -m "feat: add Celery worker configuration

- Celery app with Redis broker
- Task execution placeholder
- Configuration for task limits"
```

---

## Task 8: FastAPI Application

**Files:**
- Create: `maios/api/main.py`
- Create: `maios/api/routes/health.py`
- Create: `tests/integration/test_api.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "MAIOS"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_api.py -v
```
Expected: FAIL with "No module named 'maios.api.main'"

**Step 3: Write health route**

```python
# maios/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "maios",
    }
```

**Step 4: Write main application**

```python
# maios/api/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from maios.api.routes import health
from maios.core.config import settings
from maios.core.database import close_db, init_db
from maios.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title="MAIOS",
    description="Metamorphic AI Orchestration System",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MAIOS",
        "version": "0.1.0",
        "status": "running",
    }
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/integration/test_api.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/api/ tests/integration/test_api.py
git commit -m "feat: add FastAPI application

- Main app with lifespan management
- Health check endpoint
- Database init on startup"
```

---

## Task 9: Projects API

**Files:**
- Create: `maios/api/routes/projects.py`
- Create: `maios/models/schemas.py`
- Update: `maios/api/main.py`
- Create: `tests/integration/test_projects_api.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_projects_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project():
    """Test project creation."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/projects",
            json={
                "name": "Test Project",
                "description": "A test project",
                "initial_request": "Build a REST API",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects():
    """Test listing projects."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_project():
    """Test getting a specific project."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create first
        create_response = await client.post(
            "/api/projects",
            json={"name": "Test Project"},
        )
        project_id = create_response.json()["id"]

        # Then get
        response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_projects_api.py -v
```
Expected: FAIL with "404 Not Found"

**Step 3: Write schemas**

```python
# maios/models/schemas.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from maios.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_request: Optional[str] = None
    tech_stack: list[str] = []
    constraints: dict = {}


class ProjectRead(BaseModel):
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
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
```

**Step 4: Write projects route**

```python
# maios/api/routes/projects.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maios.core.database import get_session
from maios.models.project import Project, ProjectStatus
from maios.models.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    session: SessionDep,
):
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
    session: SessionDep,
    status: ProjectStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all projects."""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.offset(offset).limit(limit).order_by(Project.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    session: SessionDep,
):
    """Get a specific project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    session: SessionDep,
):
    """Update a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await session.commit()
    await session.refresh(project)
    return project
```

**Step 5: Update main.py to include projects router**

```python
# Add to maios/api/main.py imports
from maios.api.routes import health, projects

# Add after health router
app.include_router(projects.router)
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/integration/test_projects_api.py -v
```
Expected: PASS

**Step 7: Commit**

```bash
git add maios/api/ maios/models/schemas.py tests/integration/test_projects_api.py
git commit -m "feat: add Projects API

- Create, list, get, update endpoints
- ProjectCreate/Read/Update schemas
- Integration tests"
```

---

## Task 10: Agents API

**Files:**
- Create: `maios/api/routes/agents.py`
- Update: `maios/models/schemas.py`
- Update: `maios/api/main.py`
- Create: `tests/integration/test_agents_api.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_agents_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_agent():
    """Test agent creation."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/agents",
            json={
                "name": "Dev-Agent-1",
                "role": "Backend Developer",
                "persona": "A skilled backend developer",
                "skill_tags": ["code", "test"],
                "permissions": ["file:read", "file:write"],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Dev-Agent-1"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_agents():
    """Test listing agents."""
    from maios.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/agents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_agents_api.py -v
```
Expected: FAIL with "404 Not Found"

**Step 3: Add Agent schemas to schemas.py**

```python
# Add to maios/models/schemas.py
from maios.models.agent import AgentStatus


class AgentCreate(BaseModel):
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
    name: Optional[str] = None
    role: Optional[str] = None
    persona: Optional[str] = None
    status: Optional[AgentStatus] = None
    system_prompt: Optional[str] = None
```

**Step 4: Write agents route**

```python
# maios/api/routes/agents.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maios.core.database import get_session
from maios.models.agent import Agent, AgentStatus
from maios.models.schemas import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=AgentRead, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    session: SessionDep,
):
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
    session: SessionDep,
    status: AgentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all agents."""
    query = select(Agent).where(Agent.is_active == True)
    if status:
        query = query.where(Agent.status == status)
    query = query.offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: UUID,
    session: SessionDep,
):
    """Get a specific agent."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    session: SessionDep,
):
    """Update an agent."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await session.commit()
    await session.refresh(agent)
    return agent
```

**Step 5: Update main.py**

```python
# Add import
from maios.api.routes import health, projects, agents

# Add router
app.include_router(agents.router)
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/integration/test_agents_api.py -v
```
Expected: PASS

**Step 7: Commit**

```bash
git add maios/api/ maios/models/schemas.py tests/integration/test_agents_api.py
git commit -m "feat: add Agents API

- Create, list, get, update endpoints
- AgentCreate/Read/Update schemas
- Integration tests"
```

---

## Task 11: WebSocket Support

**Files:**
- Create: `maios/api/websocket.py`
- Update: `maios/api/main.py`
- Create: `tests/integration/test_websocket.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_websocket.py
import pytest
from starlette.testclient import TestClient


def test_websocket_connection():
    """Test WebSocket connection."""
    from maios.api.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Send a ping
        websocket.send_json({"type": "ping"})
        # Receive response
        data = websocket.receive_json()
        assert data["type"] == "pong"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_websocket.py -v
```
Expected: FAIL with "404 Not Found"

**Step 3: Write WebSocket handler**

```python
# maios/api/websocket.py
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: dict[str, Any], websocket: WebSocket):
        """Send a message to a specific connection."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connections."""
        for connection in self.active_connections:
            await connection.send_json(message)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint handler."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_message({"type": "pong"}, websocket)
            else:
                # Echo back for now (will be replaced with event routing)
                await manager.send_message(
                    {"type": "echo", "data": message},
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Step 4: Update main.py**

```python
# Add import
from maios.api.websocket import websocket_endpoint

# Add route (after app creation)
@app.websocket("/ws")
async def websocket_route(websocket):
    await websocket_endpoint(websocket)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/integration/test_websocket.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/api/websocket.py maios/api/main.py tests/integration/test_websocket.py
git commit -m "feat: add WebSocket support

- Connection manager for active connections
- WebSocket endpoint at /ws
- Ping/pong and echo handlers"
```

---

## Task 12: CLI Entry Point

**Files:**
- Create: `maios/cli/main.py`
- Create: `tests/unit/test_cli.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_cli.py
from typer.testing import CliRunner


def test_cli_version():
    """Test CLI version command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "MAIOS" in result.output


def test_cli_help():
    """Test CLI help command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Commands" in result.output
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_cli.py -v
```
Expected: FAIL with "No module named 'maios.cli.main'"

**Step 3: Write CLI**

```python
# maios/cli/main.py
import typer
from rich.console import Console

app = typer.Typer(
    name="maios",
    help="Metamorphic AI Orchestration System",
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print("MAIOS version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """MAIOS - Metamorphic AI Orchestration System."""
    pass


@app.command()
def server():
    """Start the API server."""
    import uvicorn

    console.print("[bold cyan]Starting MAIOS API server...[/bold cyan]")
    uvicorn.run(
        "maios.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


@app.command()
def worker():
    """Start a Celery worker."""
    console.print("[bold cyan]Starting MAIOS worker...[/bold cyan]")
    from maios.workers.celery_app import app as celery_app

    celery_app.worker_main(["worker", "--loglevel=info"])


@app.command()
def version_cmd():
    """Show version information."""
    console.print("[bold]MAIOS[/bold] version [cyan]0.1.0[/cyan]")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_cli.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add maios/cli/ tests/unit/test_cli.py
git commit -m "feat: add CLI entry point

- Typer-based CLI with server and worker commands
- Version display
- Rich console output"
```

---

## Task 13: CLI Project Commands

**Files:**
- Create: `maios/cli/project.py`
- Update: `maios/cli/main.py`
- Create: `tests/unit/test_cli_project.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_cli_project.py
from typer.testing import CliRunner


def test_project_list():
    """Test project list command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["project", "list"])

    assert result.exit_code == 0


def test_project_create():
    """Test project create command."""
    from maios.cli.main import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["project", "create", "Test Project", "--description", "A test"],
    )

    # Should succeed or fail gracefully
    assert result.exit_code in [0, 1]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_cli_project.py -v
```
Expected: FAIL with "No such command 'project'"

**Step 3: Write project CLI**

```python
# maios/cli/project.py
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from maios.core.config import settings

app = typer.Typer(help="Project management commands")
console = Console()

API_BASE = f"http://localhost:8000/api"


@app.command("list")
def list_projects():
    """List all projects."""
    try:
        response = httpx.get(f"{API_BASE}/projects")
        response.raise_for_status()
        projects = response.json()

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Phase", style="magenta")

        for p in projects:
            table.add_row(
                str(p["id"])[:8],
                p["name"],
                p["status"],
                p.get("orchestrator_phase", "N/A"),
            )

        console.print(table)
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to MAIOS server[/red]")
        console.print("[yellow]Make sure the server is running: maios server[/yellow]")
        raise typer.Exit(1)


@app.command("create")
def create_project(
    name: str = typer.Argument(..., help="Project name"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    request: Optional[str] = typer.Option(None, "--request", "-r"),
):
    """Create a new project."""
    payload = {"name": name}
    if description:
        payload["description"] = description
    if request:
        payload["initial_request"] = request

    try:
        response = httpx.post(f"{API_BASE}/projects", json=payload)
        response.raise_for_status()
        project = response.json()

        console.print(f"[green]Created project:[/green] {project['name']}")
        console.print(f"[cyan]ID:[/cyan] {project['id']}")
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to MAIOS server[/red]")
        raise typer.Exit(1)


@app.command("status")
def project_status(
    project_id: str = typer.Argument(..., help="Project ID"),
):
    """Show project status."""
    try:
        response = httpx.get(f"{API_BASE}/projects/{project_id}")
        response.raise_for_status()
        project = response.json()

        console.print(f"[bold]{project['name']}[/bold]")
        console.print(f"Status: [yellow]{project['status']}[/yellow]")
        console.print(f"Phase: [magenta]{project['orchestrator_phase']}[/magenta]")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print("[red]Project not found[/red]")
        raise typer.Exit(1)
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to MAIOS server[/red]")
        raise typer.Exit(1)
```

**Step 4: Update main.py**

```python
# Add import
from maios.cli import project

# Register sub-app
app.add_typer(project.app, name="project")
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_cli_project.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/cli/ tests/unit/test_cli_project.py
git commit -m "feat: add CLI project commands

- project list with table display
- project create command
- project status command"
```

---

## Task 14: Skills Registry Base

**Files:**
- Create: `maios/skills/base.py`
- Create: `maios/skills/registry.py`
- Create: `tests/unit/test_skills.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_skills.py
import pytest


def test_skill_base_class():
    """Test skill base class structure."""
    from maios.skills.base import BaseSkill

    class TestSkill(BaseSkill):
        name = "test"
        description = "A test skill"

        async def execute(self, **kwargs):
            return {"result": "ok"}

    skill = TestSkill()
    assert skill.name == "test"
    assert skill.description == "A test skill"


def test_skill_registry():
    """Test skill registry."""
    from maios.skills.registry import SkillRegistry

    registry = SkillRegistry()
    assert registry is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_skills.py -v
```
Expected: FAIL with "No module named 'maios.skills.base'"

**Step 3: Write skill base**

```python
# maios/skills/base.py
from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Base class for all skills."""

    name: str
    description: str
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}
    required_permissions: list[str] = []

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the skill."""
        pass

    def validate_permissions(self, agent_permissions: list[str]) -> bool:
        """Check if agent has required permissions."""
        return all(p in agent_permissions for p in self.required_permissions)
```

**Step 4: Write skill registry**

```python
# maios/skills/registry.py
from typing import Any, Type

from maios.skills.base import BaseSkill


class SkillRegistry:
    """Registry for available skills."""

    def __init__(self):
        self._skills: dict[str, Type[BaseSkill]] = {}

    def register(self, skill_class: Type[BaseSkill]) -> None:
        """Register a skill class."""
        self._skills[skill_class.name] = skill_class

    def get(self, name: str) -> Type[BaseSkill] | None:
        """Get a skill class by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def get_skill(self, name: str, **kwargs) -> BaseSkill | None:
        """Instantiate a skill by name."""
        skill_class = self.get(name)
        if skill_class:
            return skill_class(**kwargs)
        return None


# Global registry
registry = SkillRegistry()


def register_skill(skill_class: Type[BaseSkill]) -> Type[BaseSkill]:
    """Decorator to register a skill."""
    registry.register(skill_class)
    return skill_class
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_skills.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/skills/base.py maios/skills/registry.py tests/unit/test_skills.py
git commit -m "feat: add skills registry base

- BaseSkill abstract class
- SkillRegistry for skill management
- register_skill decorator"
```

---

## Task 15: Built-in Skills - Execute Code

**Files:**
- Create: `maios/skills/builtin/execute_code.py`
- Update: `maios/skills/builtin/__init__.py`
- Create: `tests/unit/test_execute_code.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_execute_code.py
import pytest


@pytest.mark.asyncio
async def test_execute_code_skill_exists():
    """Test execute_code skill is registered."""
    from maios.skills.builtin.execute_code import ExecuteCodeSkill

    skill = ExecuteCodeSkill()
    assert skill.name == "execute_code"
    assert "exec" in skill.required_permissions


@pytest.mark.asyncio
async def test_execute_code_skill_validates_input():
    """Test execute_code validates input."""
    from maios.skills.builtin.execute_code import ExecuteCodeSkill

    skill = ExecuteCodeSkill()
    result = await skill.execute(code="print('hello')", language="python")

    # Result will vary based on implementation
    assert "status" in result or "error" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_execute_code.py -v
```
Expected: FAIL with "No module named 'maios.skills.builtin.execute_code'"

**Step 3: Write execute_code skill**

```python
# maios/skills/builtin/execute_code.py
from typing import Any

from maios.skills.base import BaseSkill
from maios.skills.registry import register_skill


@register_skill
class ExecuteCodeSkill(BaseSkill):
    """Execute code in a sandboxed environment."""

    name = "execute_code"
    description = "Execute Python or JavaScript code in a sandbox"
    required_permissions = ["exec"]

    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to execute"},
            "language": {"type": "string", "enum": ["python", "javascript"]},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["code", "language"],
    }

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute code in sandbox.

        Note: Actual sandbox execution will be implemented in MetaContainer phase.
        This is a placeholder that validates input.
        """
        if language not in ["python", "javascript"]:
            return {
                "status": "error",
                "error": f"Unsupported language: {language}",
            }

        if not code.strip():
            return {
                "status": "error",
                "error": "No code provided",
            }

        # Placeholder - actual execution via MetaContainer
        return {
            "status": "pending",
            "message": "Code execution requires MetaContainer (Phase 3)",
            "code_length": len(code),
            "language": language,
        }
```

**Step 4: Update builtin/__init__.py**

```python
# maios/skills/builtin/__init__.py
from maios.skills.builtin.execute_code import ExecuteCodeSkill

__all__ = [
    "ExecuteCodeSkill",
]
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_execute_code.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add maios/skills/builtin/ tests/unit/test_execute_code.py
git commit -m "feat: add execute_code skill

- ExecuteCodeSkill with input validation
- Auto-registration with decorator
- Placeholder for MetaContainer execution"
```

---

## Summary

This implementation plan covers Phase 1 core infrastructure:

1. **Project Scaffolding** - Directory structure and dependencies
2. **Docker Infrastructure** - postgres, redis, api, worker, beat
3. **Configuration Module** - Environment-based settings
4. **Database Connection** - Async SQLAlchemy with SQLModel
5. **Core Data Models** - Agent, Task, Project, Memory
6. **Redis Connection** - Async Redis client
7. **Celery Setup** - Task queue configuration
8. **FastAPI Application** - Main app with lifespan
9. **Projects API** - CRUD endpoints
10. **Agents API** - CRUD endpoints
11. **WebSocket Support** - Real-time communication
12. **CLI Entry Point** - Typer-based CLI
13. **CLI Project Commands** - Project management
14. **Skills Registry Base** - Plugin architecture
15. **Built-in Skills** - Execute code skill

**Remaining for Phase 1 (future tasks):**
- Orchestrator State Machine (LangGraph)
- Agent Runtime with Z.ai integration
- Memory System with pgvector
- Additional built-in skills
- Task execution worker
- Comprehensive testing

---

*Last updated: 2025-02-12*
