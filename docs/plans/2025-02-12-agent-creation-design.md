# MAIOS Agent Creation System Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Agent Configuration Model

```python
class AgentConfig(SQLModel, table=True):
    # Identity
    id: UUID
    name: str                      # e.g., "Architect-X"
    role: str                      # e.g., "System Architect"

    # Model Configuration
    model_provider: str            # "z.ai", "openai", "anthropic"
    model_name: str                # "glm-4-plus", "gpt-4", "claude-3-opus"

    # Behavior
    persona: str                   # Full persona description
    goals: list[str]               # Agent's objectives

    # Capabilities
    skill_tags: list[str]          # ["code", "design", "review", "test"]
    permissions: list[str]         # ["file:read", "file:write", "exec"]

    # Communication
    communication_access: list[str] # Channel IDs agent can use

    # Prompt Configuration
    system_prompt: str             # Base system prompt
    developer_prompt: str          # Additional context layer

    # Performance
    performance_score: float = 0.0  # 0-100 weighted score

    # Memory
    working_memory_limit: int = 10  # Max items in working memory

    # Metadata
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
```

---

## 2. Creation Wizard Flow

### Step 1: Identity

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 1: IDENTITY                                                  │
│                                                                    │
│  Name: [_____________________________]                             │
│                                                                    │
│  Role: [Dropdown ▼] or Custom                                      │
│        ┌─────────────────────────────────┐                         │
│        │ System Architect               │                         │
│        │ Backend Developer              │                         │
│        │ Frontend Developer             │                         │
│        │ QA Engineer                    │                         │
│        │ DevOps Engineer                │                         │
│        │ Technical Writer               │                         │
│        │ Custom Role...                 │                         │
│        └─────────────────────────────────┘                         │
│                                                                    │
│  [Next →]                                                          │
└────────────────────────────────────────────────────────────────────┘
```

### Step 2: Persona & Goals

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 2: PERSONA & GOALS                                           │
│                                                                    │
│  Persona:                                                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ You are a meticulous system architect who                  │   │
│  │ specializes in designing scalable microservices...         │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  Goals:                                                            │
│  [+ Add Goal]                                                      │
│  • Design maintainable, scalable architectures                    │
│  • Ensure security best practices                                 │
│  • Document decisions for future reference                        │
│                                                                    │
│  [← Back]                                    [Next →]             │
└────────────────────────────────────────────────────────────────────┘
```

### Step 3: Model & Capabilities

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 3: MODEL & CAPABILITIES                                      │
│                                                                    │
│  Model Provider: [z.ai ▼]                                          │
│  Model:          [glm-4-plus ▼]                                    │
│                                                                    │
│  Skills:                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ ☑ code   │ │ ☑ design │ │ ☐ review │ │ ☑ test   │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ ☐ docs   │ │ ☐ git    │ │ ☑ search │ │ ☐ deploy │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                    │
│  [← Back]                                    [Next →]             │
└────────────────────────────────────────────────────────────────────┘
```

### Step 4: Permissions

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 4: PERMISSIONS                                               │
│                                                                    │
│  File Access:    [Read/Write ▼]                                    │
│  Code Execution: [☑ Allowed]                                       │
│  Network Access: [☐ Disabled]                                      │
│  Git Operations: [Read/Write ▼]                                    │
│  Memory Access:  [Team + Project ▼]                                │
│                                                                    │
│  Communication Channels:                                           │
│  [☑ Web UI] [☑ VSCode] [☐ Slack] [☐ Discord]                      │
│                                                                    │
│  [← Back]                                    [Next →]             │
└────────────────────────────────────────────────────────────────────┘
```

### Step 5: Prompt Configuration

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 5: PROMPT CONFIGURATION                                      │
│                                                                    │
│  System Prompt (Base):                                             │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ # Role                                                      │   │
│  │ You are {{role}} with expertise in...                      │   │
│  │                                                            │   │
│  │ # Guidelines                                                │   │
│  │ - Always think before responding                           │   │
│  │ - Consider security implications                           │   │
│  │ - Document your reasoning                                  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  Developer Prompt (Context Layer):                                 │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Project: {{project_name}}                                  │   │
│  │ Stack: {{project_stack}}                                   │   │
│  │ You have access to {{skills}}                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  [Preview Prompt] [← Back]           [Create Agent]                │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Prompt Tuning Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│  Agent: Architect-X                    [Active ●] [Edit Mode: ON]   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SYSTEM PROMPT                                              │   │
│  │  ─────────────────────────────────────────────────────────── │   │
│  │  # Role                                                     │   │
│  │  You are a senior system architect specializing in          │   │
│  │  distributed systems and microservices.                     │   │
│  │                                                             │   │
│  │  # Responsibilities                                         │   │
│  │  - Design system architecture                              │   │
│  │  - Evaluate trade-offs                                     │   │
│  │  - Create technical specifications                          │   │
│  │                                                             │   │
│  │  # Communication Style                                      │   │
│  │  - Be precise and technical                                │   │
│  │  - Use diagrams when helpful                               │   │
│  │  - Explain rationale for decisions                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  VARIABLES ({{variable}} syntax)                            │   │
│  │  ─────────────────────────────────────────────────────────── │   │
│  │  {{project_name}}    : "E-Commerce Platform"                │   │
│  │  {{tech_stack}}      : "Python, FastAPI, PostgreSQL"        │   │
│  │  {{constraints}}     : "Must support 10k RPS"               │   │
│  │  [+ Add Variable]                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LIVE PREVIEW (Rendered Prompt)                             │   │
│  │  ─────────────────────────────────────────────────────────── │   │
│  │  # Role                                                     │   │
│  │  You are a senior system architect...                       │   │
│  │  Working on: E-Commerce Platform                            │   │
│  │  Using: Python, FastAPI, PostgreSQL                         │   │
│  │  Constraints: Must support 10k RPS                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Test with Sample Task]         [Save Draft]     [Deploy Now]     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Hot-Deploy Process

```
1. USER CLICKS "DEPLOY NOW"
   - Validate prompt syntax
   - Check for variable completeness
   - Store new version in database
                │
                ▼
2. NOTIFY AGENT RUNTIME
   - Publish config update to Redis channel
   - Agent runtime subscribes to config changes
   - New config loaded on next task cycle
                │
                ▼
3. AGENT ACKNOWLEDGES
   - Agent logs: "Config updated to v2.3"
   - UI shows: "Architect-X updated" notification
   - Audit trail records: who, what, when
```

---

## 5. Version Control

### Version Model

```python
class AgentConfigVersion(SQLModel, table=True):
    id: UUID
    agent_id: UUID
    version: int
    config_snapshot: dict          # Full config at this version
    changed_by: str                # User or "agent:self"
    change_reason: str             # "Manual edit", "Self-improvement"
    created_at: datetime
```

### Version Features

- Rollback available to any previous version
- Diff view between versions
- Change history in agent detail panel

---

## 6. Predefined Roles

| Role | Default Skills | Default Permissions |
|------|----------------|---------------------|
| System Architect | design, review, docs | file:read, memory:read |
| Backend Developer | code, test, git | file:read, file:write, exec |
| Frontend Developer | code, design, test | file:read, file:write |
| QA Engineer | test, code, review | file:read, exec |
| DevOps Engineer | code, deploy, git | file:read, file:write, exec, network |
| Technical Writer | docs, review | file:read, file:write |

---

## 7. Permission Scopes

| Permission | Description |
|------------|-------------|
| `file:read` | Read files in project |
| `file:write` | Create/modify files |
| `exec` | Execute code in sandbox |
| `network` | Make external network requests |
| `git:read` | Read git history |
| `git:write` | Commit and push changes |
| `memory:read` | Read from knowledge base |
| `memory:write` | Write to knowledge base |
| `escalate` | Can escalate to human |

---

## 8. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/agents` | GET | List all agents |
| `/api/agents` | POST | Create new agent |
| `/api/agents/{id}` | GET | Agent details |
| `/api/agents/{id}` | PATCH | Update agent |
| `/api/agents/{id}` | DELETE | Delete/deactivate agent |
| `/api/agents/{id}/versions` | GET | List config versions |
| `/api/agents/{id}/versions/{v}` | GET | Get specific version |
| `/api/agents/{id}/rollback/{v}` | POST | Rollback to version |
| `/api/agents/{id}/deploy` | POST | Hot-deploy config |
| `/api/roles` | GET | List predefined roles |

---

## 9. Variable System

### Built-in Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{{agent_name}}` | Agent config | "Architect-X" |
| `{{agent_role}}` | Agent config | "System Architect" |
| `{{agent_skills}}` | Agent config | "code, design, review" |
| `{{project_name}}` | Current project | "E-Commerce Platform" |
| `{{project_stack}}` | Current project | "Python, FastAPI" |
| `{{current_date}}` | System | "2025-02-12" |

### Custom Variables

Users can define custom variables in the prompt tuning panel:

```
{{coding_style}} = "Clean, well-documented code with type hints"
{{max_line_length}} = "88"
```

---

*Last updated: 2025-02-12*
