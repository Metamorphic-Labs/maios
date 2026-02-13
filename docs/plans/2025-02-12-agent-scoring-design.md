# MAIOS Agent Scoring System Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Scoring Model

```python
class AgentScore(BaseModel):
    agent_id: UUID

    # Raw metrics (rolling window, last 30 days)
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_reassigned: int = 0
    human_overrides: int = 0

    total_completion_time_seconds: int = 0
    avg_completion_time_seconds: float = 0.0

    # Derived scores (0-100)
    success_rate_score: float = 0.0
    speed_score: float = 0.0
    reliability_score: float = 0.0

    # Confidence tracking
    self_confidence_avg: float = 0.0  # Agent's own confidence ratings

    # Final weighted score
    overall_score: float = 0.0

    # Score trend
    score_trend: Literal["improving", "stable", "declining"] = "stable"

    last_updated: datetime
```

---

## 2. Metric Calculations

| Metric | Formula | Score Range |
|--------|---------|-------------|
| Success Rate | `(completed / (completed + failed)) * 100` | 0-100 |
| Speed Score | `benchmark_time / actual_time * 100` (capped at 100) | 0-100 |
| Reliability | `100 - ((reassigned + overrides) / total * 100)` | 0-100 |

---

## 3. Weighted Scoring

### Weight Configuration

```python
class ScoringWeights(BaseModel):
    """Weights for overall score calculation. Must sum to 1.0"""

    success_rate: float = 0.4      # 40% - Most important
    speed: float = 0.25            # 25% - Important but secondary
    reliability: float = 0.25      # 25% - Equally important
    confidence: float = 0.10       # 10% - Self-awareness indicator
```

### Overall Score Calculation

```python
def calculate_overall_score(agent: Agent, weights: ScoringWeights) -> float:
    score = (
        agent.success_rate_score * weights.success_rate +
        agent.speed_score * weights.speed +
        agent.reliability_score * weights.reliability +
        agent.self_confidence_avg * weights.confidence
    )
    return round(score, 2)
```

---

## 4. Delegation Influence

### Delegation Algorithm

```
When Orchestrator delegates a task:

1. CANDIDATE SELECTION
   Filter agents by:
   - Required skill tags match
   - Agent is active and healthy
   - Agent has capacity (not at task limit)
   - Agent has permission for task type
                │
                ▼
2. SCORING & RANKING
   For each candidate:

   base_score = agent.overall_score

   # Adjust for task-specific history
   if agent.has_completed_similar_tasks(task):
       base_score += 10  # Similarity bonus

   # Adjust for current workload
   workload_factor = 1 - (agent.current_tasks / max_tasks)
   adjusted_score = base_score * workload_factor

   # Trend bonus
   if agent.score_trend == "improving":
       adjusted_score += 5
   elif agent.score_trend == "declining":
       adjusted_score -= 5
                │
                ▼
3. SELECTION
   # Option A: Deterministic (highest score wins)
   selected = max(candidates, key=lambda a: a.adjusted_score)

   # Option B: Probabilistic (weighted random)
   selected = weighted_choice(candidates)
```

### Delegation API

```python
class DelegationRequest(BaseModel):
    task_id: UUID
    required_skills: list[str]
    complexity: Literal["low", "medium", "high"]
    deadline: Optional[datetime]

class DelegationResult(BaseModel):
    selected_agent_id: UUID
    score: float
    reasoning: str          # "Selected based on 94.2 score + similar task history"
    alternatives: list[dict]  # Other candidates with scores
```

---

## 5. Performance Dashboard UI

### Top Performers

```
┌──────────────────────────────────────────────────────────────────────┐
│  TOP PERFORMERS                                                      │
│  ─────────────────────────────────────────────────────────────────── │
│                                                                      │
│  1. Architect-X    ████████████████████ 94.2  ↑ improving           │
│  2. Dev-Luna       ███████████████████░ 89.7  → stable              │
│  3. QA-Bot         ██████████████████░░ 85.3  ↑ improving           │
│  4. Dev-Max        █████████████████░░░ 78.1  ↓ declining           │
│  5. Doc-Writer     ████████████████░░░░ 72.4  → stable              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Score Breakdown

```
┌──────────────────────────────────────────────────────────────────────┐
│  SCORE BREAKDOWN (Architect-X)                                       │
│  ─────────────────────────────────────────────────────────────────── │
│                                                                      │
│  Success Rate    ████████████████████████ 96% (40% weight)          │
│  Speed           ████████████████████░░░░ 92% (25% weight)          │
│  Reliability     █████████████████████░░░ 94% (25% weight)          │
│  Confidence      ███████████████████░░░░░ 88% (10% weight)          │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────── │
│  OVERALL: 94.2                                                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Performance Heatmap

```
┌──────────────────────────────────────────────────────────────────────┐
│  PERFORMANCE HEATMAP (Last 7 Days)                                   │
│  ─────────────────────────────────────────────────────────────────── │
│                                                                      │
│         Mon  Tue  Wed  Thu  Fri  Sat  Sun                           │
│  Arch   🟢   🟢   🟢   🟡   🟢   🟢   ⚪                             │
│  Luna   🟢   🟡   🟢   🟢   🟢   ⚪   ⚪                             │
│  QA     🟢   🟢   🔴   🟢   🟢   🟢   ⚪                             │
│  Max    🟡   🟡   🔴   🟡   🟢   ⚪   ⚪                             │
│                                                                      │
│  🟢 High (90+)  🟡 Medium (70-89)  🔴 Low (<70)  ⚪ No data         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Score Trend

```
┌──────────────────────────────────────────────────────────────────────┐
│  SCORE TREND (Last 30 Days)                                          │
│  ─────────────────────────────────────────────────────────────────── │
│                                                                      │
│  100 ┤                                                               │
│   95 ┤              ●──●──●                                          │
│   90 ┤         ●──●       ●──●                                       │
│   85 ┤    ●──●                   ●──●                                │
│   80 ┤ ●──┘                           ●                              │
│   75 ┤                              ●                                │
│      └────────────────────────────────────────────────────────────  │
│        Week 1   Week 2   Week 3   Week 4                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent Detail Score Card

```
┌─────────────────────────────────────────────────────────────────────┐
│  ARCHITECT-X                                              [Edit]    │
│  System Architect                                     Overall: 94.2  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────────────────────┐  │
│  │  METRICS (30 days)  │  │  TASK HISTORY                       │  │
│  │                     │  │                                     │  │
│  │  Completed: 47      │  │  ✓ Design API structure    (2.3h)  │  │
│  │  Failed:    2       │  │  ✓ Database schema review  (1.1h)  │  │
│  │  Reassigned: 1      │  │  ✓ Auth flow design        (3.5h)  │  │
│  │  Overrides: 0       │  │  ✗ Cache layer design      (err)   │  │
│  │                     │  │  ✓ Rate limiting spec      (0.8h)  │  │
│  │  Avg Time: 1.8h     │  │  [View Full History]                │  │
│  └─────────────────────┘  └─────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STRENGTHS                      IMPROVEMENT AREAS            │   │
│  │  ────────────────────────────   ──────────────────────────── │   │
│  │  • Architecture design          • Documentation              │   │
│  │  • API design                   • Speed on complex tasks     │   │
│  │  • Security review                                            │   │
│  │  • Database modeling                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [View Detailed Analytics]    [Compare with Team]    [Export PDF]  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Score Trend Detection

### Algorithm

```python
def detect_trend(scores: list[float], window: int = 7) -> str:
    """Detect score trend over recent window."""
    if len(scores) < window:
        return "stable"

    recent = scores[-window:]
    earlier = scores[-window*2:-window] if len(scores) >= window*2 else scores[:-window]

    recent_avg = sum(recent) / len(recent)
    earlier_avg = sum(earlier) / len(earlier)

    diff = recent_avg - earlier_avg

    if diff > 2:
        return "improving"
    elif diff < -2:
        return "declining"
    else:
        return "stable"
```

---

## 8. Score History

### History Model

```python
class ScoreHistory(SQLModel, table=True):
    id: UUID
    agent_id: UUID
    timestamp: datetime

    # Snapshot of all metrics
    overall_score: float
    success_rate_score: float
    speed_score: float
    reliability_score: float
    confidence_score: float

    # Raw metrics at this point
    tasks_completed: int
    tasks_failed: int
```

### Retention

- Daily snapshots retained for 90 days
- Weekly aggregates retained for 1 year
- Monthly aggregates retained indefinitely

---

## 9. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/agents/{id}/score` | GET | Agent score details |
| `/api/agents/{id}/score/history` | GET | Score history |
| `/api/agents/scores/leaderboard` | GET | Top performers |
| `/api/agents/scores/heatmap` | GET | Performance heatmap data |
| `/api/scores/weights` | GET | Current weight configuration |
| `/api/scores/weights` | PUT | Update weights (admin) |

---

## 10. Score Impact on System

### Delegation Priority

Higher-scoring agents:
- Receive more complex tasks
- Get priority in task assignment
- Are preferred for critical work

### Self-Improvement Triggers

Low scores trigger:
- Self-reflection cycles
- Prompt optimization suggestions
- Skill training recommendations

### Team Composition

Team leaders are selected based on:
- Highest overall score in team scope
- Strong reliability score
- Good communication patterns

---

## 11. Reporting

### Daily Summary

```
Daily Performance Summary - 2025-02-12

Top Performers:
1. Architect-X (94.2) - 5 tasks completed
2. Dev-Luna (89.7) - 8 tasks completed

Improving:
- QA-Bot (+3.2 points)

Attention Needed:
- Dev-Max (-2.1 points, 2 failures today)

System Metrics:
- Average Score: 82.4
- Tasks Completed: 47
- Success Rate: 94%
```

### Weekly Report

- Trend analysis for all agents
- Score distribution histogram
- Improvement/decline rankings
- Recommended actions for low performers

---

*Last updated: 2025-02-12*
