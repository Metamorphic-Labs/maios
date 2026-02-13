# MAIOS Phase 1 Design Document

**Metamorphic AI Orchestration System (M.A.I.O.S)**

*Version: 1.0 | Date: 2025-02-12 | Status: Approved*

---

## Executive Summary

MAIOS is a programmable AI organization runtime — a platform for deploying, coordinating, and managing autonomous AI agents that collaborate to execute complex software development tasks.

### Strategic Positioning

- **Primary Identity:** Platform/Product
- **Initial Operational Mode:** Software Development Factory
- **Quality Target:** Production-MVP
- **Development Approach:** Phased Intelligence-First MVP

---

## 1. Architecture Overview

### 1.1 Approach: Modular Monolith with Async Workers

```
maios/
├── maios/
│   ├── api/routes/           # FastAPI endpoints
│   ├── core/
│   │   ├── orchestrator/     # State machine + phases
│   │   ├── memory/           # Hybrid memory service
│   │   └── agent_runtime.py  # Agent execution loop
│   ├── models/               # SQLModel definitions
│   ├── skills/builtin/       # 8 built-in skills
│   ├── workers/              # Celery tasks
│   ├── sandbox/              # Docker execution
│   └── cli/                  # Typer CLI
├── migrations/
├── tests/
└── docker/
```

### 1.2 System Flow

```
User Request → Orchestrator.PLAN → Task Graph
                                        ↓
                      Orchestrator.DELEGATE → Agent Assignment
                                        ↓
                      Agent Runtime → Z.ai + Skills
                                        ↓
                      Memory Store → Orchestrator.MONITOR
                                        ↓
                      COMPLETE or ESCALATE → Result
```

---

## 2. Core Components

### 2.1 Orchestrator State Machine (LangGraph)

| Phase | Trigger | Action |
|-------|---------|--------|
| PLAN | New project | Decompose request into task graph |
| DELEGATE | Tasks ready | Score agents, assign best match |
| MONITOR | Continuous | Check progress, detect issues |
| ESCALATE | Blocked/conflict | Auto-resolve or notify human |
| REASSIGN | Agent failing | Move tasks to healthy agent |
| COMPLETE | All done | Summarize, store lessons |

### 2.2 Agent Engine

- Persistent agents with performance tracking
- Z.ai integration with tool calling
- Self-reflection after each task
- Working memory + long-term memory

### 2.3 Memory System

| Layer | Technology | Purpose |
|-------|------------|---------|
| Ephemeral | Redis | Session state, working memory |
| Structured | PostgreSQL | Tasks, agents, history |
| Vector | pgvector | Embeddings, similarity search |

### 2.4 Skill Registry (8 Built-in)

| Skill | Purpose |
|-------|---------|
| execute_code | Sandbox code execution |
| read_file / write_file | File operations |
| search_code | Ripgrep codebase search |
| list_files | Directory listing |
| search_memory | Query knowledge base |
| run_tests | Execute test suite |
| git_operation | Git commands |

---

## 3. Data Models

### 3.1 Core Entities

- **Project**: User request being orchestrated
- **Agent**: AI worker with role, skills, permissions
- **Task**: Work item with hierarchy and dependencies
- **MemoryEntry**: Persistent memory with embeddings
- **Escalation**: Issue requiring attention
- **Decision**: Audit trail of orchestrator choices

### 3.2 Multi-Tenancy (Cloud-Ready)

- Organization + User models defined
- Feature-flagged: single-user local, multi-tenant cloud
- Same codebase, conditional enforcement

---

## 4. Deployment

### 4.1 Docker Compose Stack

```yaml
services:
  postgres:  # pgvector/pgvector:pg16
  redis:     # redis:7-alpine
  api:       # FastAPI on :8000
  worker:    # Celery worker
  beat:      # Celery beat scheduler
  sandbox:   # Docker-in-Docker
```

### 4.2 Configuration

| Variable | Default |
|----------|---------|
| ZAI_API_KEY | required |
| DATABASE_URL | postgresql://maios:maios@localhost:5432/maios |
| REDIS_URL | redis://localhost:6379/0 |
| DEFAULT_MODEL | glm-4-plus |
| TASK_TIMEOUT_MINUTES | 30 |
| MULTI_TENANT_MODE | false |

---

## 5. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| /api/projects | POST | Create project |
| /api/projects/{id} | GET | Project details |
| /api/projects/{id}/input | POST | Human input |
| /api/agents | GET/POST | List/create agents |
| /api/tasks | GET | List tasks |
| /api/memory/search | POST | Search knowledge |
| /ws/project/{id} | WS | Real-time updates |

---

## 6. CLI Commands

```bash
maios run task "Build a REST API"     # Start orchestration
maios run interactive                  # REPL mode
maios project list                     # List projects
maios project status <id> --watch      # Watch progress
maios agent list                       # List agents
maios agent create --name Dev1         # Create agent
maios task logs <id> -f                # Stream logs
maios server                           # Start API
maios worker                           # Start Celery
```

---

## 7. Brand Integration

Metamorphic Labs brand tokens:

| Token | Hex | Usage |
|-------|-----|-------|
| --brand-primary | #11C8D6 | Accent |
| --surface-0 | #0B1116 | Background |
| --surface-1 | #111821 | Panels |
| --fg | #C7D4E2 | Text |
| --success | #22C55E | Success |
| --danger | #EF4444 | Error |

Typography: Inter, 400/500/600/700 weights
Motion: 150-200ms, cubic-bezier(0.2, 0.8, 0.2, 1)

---

## 8. Phase 1 Success Criteria

- [ ] Orchestration loop works end-to-end
- [ ] Agents delegate and collaborate
- [ ] Memory retrieval provides context
- [ ] Failing agents get reassigned
- [ ] Code executes in sandbox
- [ ] CLI creates/monitors projects
- [ ] WebSocket streams updates
- [ ] Production-ready error handling

---

## 9. Future Phases

**Phase 2:** Teams, negotiation, VSCode extension, MetaContainer
**Phase 3:** 3D visualization, performance dashboards, prompt tuning UI

---

*Last updated: 2025-02-12*
