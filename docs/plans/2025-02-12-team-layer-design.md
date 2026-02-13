# MAIOS Team Layer Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Team Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TEAM LAYER ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                     ┌─────────────────────┐                         │
│                     │    ORCHESTRATOR     │                         │
│                     │  (Master Controller)│                         │
│                     └──────────┬──────────┘                         │
│                                │                                    │
│          ┌─────────────────────┼─────────────────────┐             │
│          │                     │                     │             │
│          ▼                     ▼                     ▼             │
│   ┌────────────┐        ┌────────────┐        ┌────────────┐       │
│   │ DEV TEAM   │        │  QA TEAM   │        │ DESIGN TEAM│       │
│   │            │        │            │        │            │       │
│   │ [Leader]   │        │ [Leader]   │        │ [Leader]   │       │
│   │ [Agent-1]  │        │ [Agent-1]  │        │ [Agent-1]  │       │
│   │ [Agent-2]  │        │ [Agent-2]  │        │ [Agent-2]  │       │
│   │            │        │            │        │            │       │
│   │ Shared:    │        │ Shared:    │        │ Shared:    │       │
│   │ - Memory   │        │ - Memory   │        │ - Memory   │       │
│   │ - Tasks    │        │ - Tasks    │        │ - Tasks    │       │
│   │ - Skills   │        │ - Skills   │        │ - Skills   │       │
│   └────────────┘        └────────────┘        └────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Team Data Model

```python
class Team(SQLModel, table=True):
    # Identity
    id: UUID
    name: str                        # e.g., "Dev Team Alpha"
    scope: str                       # e.g., "backend", "frontend", "qa"
    leader_id: UUID                  # Team leader agent

    # Shared resources
    memory_namespace: str            # Isolated memory space
    skill_tags: list[str]            # Available skills for team

    # Cross-team permissions
    can_communicate_with: list[UUID] # Other teams this team can talk to
    escalation_policy: str           # "auto", "manual", "smart"

    # Configuration
    max_members: int = 5
    task_concurrency: int = 3        # Max parallel tasks

    # Metadata
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
```

---

## 3. Team Operation Modes

### 3.1 TeamSync Mode (Internal Discussion)

Team members discuss internally to reach consensus.

```
┌────────────────────────────────────────────────────────────────────┐
│  Team members discuss internally to reach consensus                │
│                                                                    │
│  Agent-A: "I think we should use PostgreSQL"                      │
│  Agent-B: "Agreed, but we need connection pooling"                │
│  Leader: "Decision: PostgreSQL + PgBouncer"                        │
│                                                                    │
│  - Private to team                                                 │
│  - Leader has final decision authority                             │
│  - Logged to team memory                                           │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 CrossTalk Mode (Inter-Team Query)

Team A queries Team B for information.

```
Dev Team ──query──▶ QA Team
"What are the test coverage requirements?"

QA Team ──response──▶ Dev Team
"Minimum 80% coverage for new modules"

Rules:
- Must have permission in can_communicate_with
- Rate-limited to prevent spam
```

### 3.3 Escalate Mode (Orchestrator Intervention)

Team cannot resolve, escalates to Orchestrator.

```
Team: "We're blocked on API spec decision"
       ↓
Orchestrator: Analyzes, makes decision OR
              escalates to human
       ↓
Resolution sent back to team
```

### 3.4 Handoff Mode (Pipeline Continuation)

Work transfers between teams in a pipeline.

```
Dev Team ──handoff──▶ QA Team
Payload: { completed_tasks, artifacts, notes }

- Includes context transfer
- Receiving team acknowledges
- Full audit trail
```

### 3.5 Demo Mode (MetaContainer Execution)

Team work is tested in isolated container.

```
Team completes task → Spawns MetaContainer
                         ↓
                  [Sandbox Execution]
                         ↓
                  Results fed back to team

- Automatic for certain task types
- Manual trigger option
```

---

## 4. Team State Machine

```
                         ┌─────────────────┐
                         │     IDLE        │
                         │  (No active     │
                         │   tasks)        │
                         └────────┬────────┘
                                  │ Task assigned
                                  ▼
                         ┌─────────────────┐
                    ┌───▶│    WORKING      │◀───┐
                    │    │  (Executing     │    │
                    │    │   tasks)        │    │
                    │    └────────┬────────┘    │
                    │             │             │
          Reassign  │    ┌────────┴────────┐    │  Task done
          from peer │    │                 │    │  (partial)
                    │    ▼                 ▼    │
             ┌──────┴───────┐      ┌────────────┴─────┐
             │  NEGOTIATING │      │     HANDOFF      │
             │  (Internal   │      │  (Transferring   │
             │   debate)    │      │   to next team)  │
             └──────┬───────┘      └────────┬─────────┘
                    │                       │
                    │ Consensus             │ Complete
                    │ reached               │
                    ▼                       ▼
             ┌─────────────────────────────────────┐
             │            COMPLETED                │
             │     (All tasks done, ready          │
             │      for next assignment)           │
             └─────────────────────────────────────┘
                                  │
                                  │ Blocked
                                  ▼
                         ┌─────────────────┐
                         │   ESCALATED     │
                         │  (Waiting for   │
                         │   Orchestrator) │
                         └─────────────────┘
```

---

## 5. Negotiation Protocol

### Negotiation Message Model

```python
class NegotiationMessage(SQLModel):
    id: UUID
    team_id: UUID
    proposer_id: UUID          # Agent proposing
    message_type: Literal["proposal", "counter", "vote", "decision"]
    content: str

    # For proposals
    proposal: Optional[dict]   # { topic, options, deadline }

    # For votes
    vote: Optional[Literal["agree", "disagree", "abstain"]]

    # For decisions
    decision: Optional[str]
    rationale: Optional[str]

    created_at: datetime
```

### Negotiation Flow

```
1. Agent proposes: "I suggest we use React for the frontend"
2. Other agents vote: agree/disagree/abstain
3. If consensus (>60% agree): Leader confirms decision
4. If no consensus: Leader makes final call OR escalates
5. Decision logged to team memory
```

### Voting Rules

| Scenario | Threshold | Action |
|----------|-----------|--------|
| Strong consensus | >80% agree | Immediate adoption |
| Majority | >60% agree | Leader confirms |
| Split vote | 40-60% | Leader decides |
| Rejection | <40% agree | Proposal rejected |

---

## 6. Team Memory Namespace

Each team has isolated memory for:

- **Discussion History:** All TeamSync conversations
- **Decisions Made:** Architecture choices, conventions
- **Shared Context:** Project-specific knowledge
- **CrossTalk Logs:** Queries to/from other teams

### Memory Isolation

```python
class TeamMemory(SQLModel):
    team_id: UUID
    namespace: str           # Isolated key prefix
    entries: list[MemoryEntry]

    # Access control
    def can_access(self, agent_id: UUID) -> bool:
        return agent_id in self.team_members
```

---

## 7. Cross-Team Communication

### Permission Model

```python
class TeamCommunicationPermission(BaseModel):
    source_team_id: UUID
    target_team_id: UUID
    allowed_modes: list[Literal["crosstalk", "handoff"]]
    rate_limit_per_hour: int = 10
```

### Communication Log

All cross-team communication is logged:

```python
class TeamCommunicationLog(SQLModel):
    id: UUID
    source_team_id: UUID
    target_team_id: UUID
    mode: str                # "crosstalk" or "handoff"
    summary: str
    participants: list[UUID]
    timestamp: datetime
```

---

## 8. Team Performance Tracking

### Team Metrics

```python
class TeamMetrics(BaseModel):
    team_id: UUID

    # Task metrics
    tasks_completed: int
    tasks_failed: int
    avg_completion_time: float

    # Collaboration metrics
    successful_handoffs: int
    failed_handoffs: int
    escalations: int

    # Negotiation metrics
    consensus_rate: float    # % of decisions reached without escalation
    avg_decision_time: float # Time to reach consensus
```

### Team Score

Overall team score influences:

- Priority for task assignment
- Resource allocation
- Escalation threshold adjustment

---

## 9. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/teams` | GET | List all teams |
| `/api/teams` | POST | Create new team |
| `/api/teams/{id}` | GET | Team details |
| `/api/teams/{id}` | PATCH | Update team |
| `/api/teams/{id}/members` | GET | List team members |
| `/api/teams/{id}/members/{agent_id}` | POST | Add agent to team |
| `/api/teams/{id}/members/{agent_id}` | DELETE | Remove agent from team |
| `/api/teams/{id}/negotiate` | POST | Start negotiation |
| `/api/teams/{id}/handoff` | POST | Handoff to another team |
| `/ws/team/{id}` | WS | Team-specific events |

---

*Last updated: 2025-02-12*
