# MAIOS Heartbeat System Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Heartbeat Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HEARTBEAT SYSTEM ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                     ┌─────────────────────┐                         │
│                     │   HEARTBEAT         │                         │
│                     │   SCHEDULER         │                         │
│                     │   (Celery Beat)     │                         │
│                     └──────────┬──────────┘                         │
│                                │                                    │
│              Every X minutes (configurable, default: 5)             │
│                                │                                    │
│       ┌────────────────────────┼────────────────────────┐          │
│       │                        │                        │          │
│       ▼                        ▼                        ▼          │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐    │
│  │  TASK       │        │  AGENT      │        │  EXTERNAL   │    │
│  │  HEALTH     │        │  HEALTH     │        │  CHECKS     │    │
│  │  CHECK      │        │  CHECK      │        │             │    │
│  └──────┬──────┘        └──────┬──────┘        └──────┬──────┘    │
│         │                      │                      │            │
│         └──────────────────────┴──────────────────────┘            │
│                                │                                    │
│                                ▼                                    │
│                     ┌─────────────────────┐                         │
│                     │   ACTION DISPATCHER │                         │
│                     │   (Escalate,        │                         │
│                     │    Reassign,        │                         │
│                     │    Notify)          │                         │
│                     └─────────────────────┘                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Configuration

```python
class HeartbeatConfig(BaseModel):
    # Schedule
    interval_minutes: int = 5

    # Task health thresholds
    task_stalled_after_minutes: int = 30
    task_long_running_after_minutes: int = 120

    # Agent health thresholds
    agent_silent_after_minutes: int = 15
    agent_high_error_rate: float = 0.3  # 30% errors

    # External check configuration
    check_calendar: bool = False
    check_email: bool = False
    calendar_provider: str = "google"  # google, outlook, none
```

---

## 3. Task Health Check

```python
async def check_task_health():
    """
    Runs every heartbeat interval.
    Checks all active (non-completed) tasks.
    """
    active_tasks = await get_active_tasks()

    for task in active_tasks:
        # Check 1: Is task stalled?
        time_since_update = now() - task.last_updated
        if time_since_update > STALLED_THRESHOLD:
            await dispatch_action(
                action="task_stalled",
                task_id=task.id,
                severity="warning"
            )

        # Check 2: Is task running too long?
        time_since_start = now() - task.started_at
        if time_since_start > LONG_RUNNING_THRESHOLD:
            await dispatch_action(
                action="task_long_running",
                task_id=task.id,
                severity="info"
            )

        # Check 3: Has task exceeded timeout?
        if time_since_start > task.timeout_minutes:
            await dispatch_action(
                action="task_timeout",
                task_id=task.id,
                severity="critical",
                auto_escalate=True
            )
```

---

## 4. Agent Health Check

```python
async def check_agent_health():
    """
    Runs every heartbeat interval.
    Checks all active agents.
    """
    active_agents = await get_active_agents()

    for agent in active_agents:
        # Check 1: Agent heartbeat timeout
        time_since_ping = now() - agent.last_heartbeat
        if time_since_ping > AGENT_SILENT_THRESHOLD:
            await dispatch_action(
                action="agent_silent",
                agent_id=agent.id,
                severity="warning"
            )

        # Check 2: High error rate
        recent_tasks = await get_agent_recent_tasks(agent.id, limit=10)
        error_rate = count_errors(recent_tasks) / len(recent_tasks)
        if error_rate > HIGH_ERROR_THRESHOLD:
            await dispatch_action(
                action="agent_high_errors",
                agent_id=agent.id,
                severity="warning"
            )

        # Check 3: Memory pressure
        if agent.memory_usage > 0.9:
            await dispatch_action(
                action="agent_memory_pressure",
                agent_id=agent.id,
                severity="info"
            )
```

---

## 5. External Checks (Optional)

### Calendar Integration

```python
async def check_external_sources():
    if config.check_calendar:
        events = await fetch_upcoming_events(hours=24)
        for event in events:
            if event.is_deadline:
                await dispatch_action(
                    action="deadline_approaching",
                    event=event,
                    severity="info"
                )
```

### Email Integration

```python
async def check_email():
    if config.check_email:
        unread = await fetch_unread_emails()
        for email in unread:
            if email.is_urgent:
                await dispatch_action(
                    action="urgent_email",
                    email=email,
                    severity="warning"
                )
```

---

## 6. Action Types

### TASK_STALLED

| Property | Value |
|----------|-------|
| Trigger | No update for 30+ minutes |
| Actions | 1. Notify project owner, 2. Log warning, 3. Recheck in 10 min, 4. Escalate if still stalled |

### TASK_TIMEOUT

| Property | Value |
|----------|-------|
| Trigger | Task exceeded timeout_minutes |
| Actions | 1. Cancel execution, 2. Reassign or mark for human, 3. Log incident, 4. Notify user |

### AGENT_SILENT

| Property | Value |
|----------|-------|
| Trigger | No heartbeat for 15+ minutes |
| Actions | 1. Attempt restart, 2. Reassign tasks, 3. Mark as degraded, 4. Alert operations |

### AGENT_HIGH_ERRORS

| Property | Value |
|----------|-------|
| Trigger | Error rate > 30% over last 10 tasks |
| Actions | 1. Reduce assignments, 2. Trigger self-reflection, 3. Disable if persistent, 4. Log for scoring |

---

## 7. Action Dispatcher

```python
class ActionDispatcher:
    async def dispatch(self, action: HeartbeatAction):
        # Determine severity and recipients
        severity = action.severity
        recipients = await self.get_recipients(action)

        # Execute actions based on type
        match action.type:
            case "task_stalled":
                await self.handle_stalled_task(action)
            case "task_timeout":
                await self.handle_timeout(action)
            case "agent_silent":
                await self.handle_silent_agent(action)
            case "agent_high_errors":
                await self.handle_high_errors(action)

        # Send notifications
        await self.send_notifications(recipients, action)

        # Log action
        await self.log_action(action)
```

---

## 8. Notification System

### Notification Channels

```python
class NotificationDispatcher:
    async def dispatch(self, action: HeartbeatAction):
        recipients = await self.get_recipients(action)

        for recipient in recipients:
            match recipient.channel:
                case "web":
                    await self.send_web_notification(recipient, action)
                case "email":
                    await self.send_email(recipient, action)
                case "slack":
                    await self.send_slack_dm(recipient, action)

        await self.log_notification(action, recipients)
```

### Notification UI

```
┌─────────────────────────────────────────────────────────────────────┐
│  NOTIFICATIONS                                    [Mark All Read]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● [Warning]  Task #42 stalled for 45 minutes                      │
│    Agent: Architect-X | Project: E-Commerce API                    │
│    [View Task] [Reassign] [Dismiss]                2 min ago       │
│                                                                     │
│  ● [Info]     Deadline approaching: "Sprint 4 Review"              │
│    Scheduled for: Tomorrow 3:00 PM                                  │
│    [View Calendar] [Snooze]                         1 hour ago     │
│                                                                     │
│  ○ [Resolved] Agent Dev-2 recovered                                │
│    Tasks reassigned, agent back online                              │
│    [View Agent]                                     3 hours ago    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Celery Beat Configuration

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('maios')

app.conf.beat_schedule = {
    'heartbeat-check': {
        'task': 'maios.workers.heartbeat.run_health_checks',
        'schedule': 300.0,  # Every 5 minutes
    },
    'daily-summary': {
        'task': 'maios.workers.heartbeat.generate_daily_summary',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
}
```

---

## 10. Health Check Task

```python
@app.task
async def run_health_checks():
    """Main heartbeat task called by Celery Beat."""

    # Run all health checks in parallel
    results = await asyncio.gather(
        check_task_health(),
        check_agent_health(),
        check_external_sources(),
        return_exceptions=True
    )

    # Handle any exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Health check {i} failed: {result}")

    return {"status": "completed", "timestamp": datetime.utcnow()}
```

---

## 11. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/health/status` | GET | Current system health |
| `/api/health/tasks` | GET | Task health summary |
| `/api/health/agents` | GET | Agent health summary |
| `/api/notifications` | GET | List notifications |
| `/api/notifications/{id}/read` | POST | Mark as read |
| `/api/notifications/read-all` | POST | Mark all read |

---

## 12. Metrics & Monitoring

### Health Metrics

```python
class HealthMetrics(BaseModel):
    # System level
    total_agents: int
    active_agents: int
    degraded_agents: int

    total_tasks: int
    stalled_tasks: int
    long_running_tasks: int

    # Last check
    last_heartbeat: datetime
    next_heartbeat: datetime

    # Notification queue
    pending_notifications: int
```

### Monitoring Dashboard

The heartbeat system exposes metrics for monitoring:
- `maios.heartbeat.last_run` - Timestamp of last check
- `maios.heartbeat.stalled_tasks` - Count of stalled tasks
- `maios.heartbeat.degraded_agents` - Count of degraded agents
- `maios.heartbeat.notifications_sent` - Notifications sent

---

*Last updated: 2025-02-12*
