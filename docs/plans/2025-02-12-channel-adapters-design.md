# MAIOS Channel Adapters Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Adapter Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CHANNEL ADAPTER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                    ┌─────────────────────┐                          │
│                    │   ADAPTER MANAGER   │                          │
│                    │   (Registry +       │                          │
│                    │    Router)          │                          │
│                    └──────────┬──────────┘                          │
│                               │                                     │
│       ┌───────────────────────┼───────────────────────┐            │
│       │           │           │           │           │            │
│       ▼           ▼           ▼           ▼           ▼            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ Slack   │ │ Discord │ │  Web    │ │ VSCode  │ │Terminal │      │
│  │ Adapter │ │ Adapter │ │ Adapter │ │ Adapter │ │ Adapter │      │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘      │
│       │           │           │           │           │            │
│       └───────────┴───────────┴─────┬─────┴───────────┘            │
│                                     │                              │
│                                     ▼                              │
│                         ┌───────────────────┐                      │
│                         │  MESSAGE QUEUE    │                      │
│                         │  (Redis Pub/Sub)  │                      │
│                         └─────────┬─────────┘                      │
│                                   │                                │
│                                   ▼                                │
│                         ┌───────────────────┐                      │
│                         │  AGENT RUNTIME    │                      │
│                         │  (Processing)     │                      │
│                         └───────────────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Adapter Interface

All adapters implement a common interface:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from pydantic import BaseModel

class BaseAdapter(ABC):
    """Base class for all channel adapters."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the channel."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the channel."""
        ...

    @abstractmethod
    async def receive_message(self) -> AsyncIterator[IncomingMessage]:
        """Yield incoming messages from the channel."""
        ...

    @abstractmethod
    async def send_message(self, message: OutgoingMessage) -> None:
        """Send a message to the channel."""
        ...

    @abstractmethod
    async def stream_response(self, response: AsyncIterator[str]) -> None:
        """Stream a response (for channels that support it)."""
        ...
```

### Unified Message Formats

```python
class IncomingMessage(BaseModel):
    adapter_type: str           # "slack", "discord", etc.
    channel_id: str
    user_id: str
    content: str
    metadata: dict              # Adapter-specific data

class OutgoingMessage(BaseModel):
    content: str
    reply_to: Optional[str]     # Original message ID
    agent_id: str               # Which agent is responding
    stream: bool = False        # Stream or complete response
```

---

## 3. Slack Adapter

### Configuration

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...
```

### Features

| Feature | Implementation |
|---------|----------------|
| App mentions | Trigger agent response |
| DM channels | Private agent conversations |
| Thread replies | Context preservation |
| Block Kit | Rich responses (buttons, forms) |
| Streaming | Typing indicator + chunked messages |
| Slash commands | `/maios-run`, `/maios-status` |

### Event Mapping

| Slack Event | MAIOS Action |
|-------------|--------------|
| `app_mention` | Create task, respond |
| `message.im` | Private agent session |
| `reaction_added` | Feedback signal (👍 = approve) |
| `slash_command` | CLI-style operation |

---

## 4. Discord Adapter

### Configuration

```bash
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...  # Optional, limit to specific server
```

### Features

| Feature | Implementation |
|---------|----------------|
| Bot mentions | Trigger agent response |
| Thread support | Long conversations |
| Embed messages | Rich formatting |
| Slash commands | Discord Interactions |
| Voice channel status | Agent "speaking" indicator |
| Forum channels | Project-based discussions |

---

## 5. Web UI Adapter

(Already covered in Frontend & Visualization design)

### WebSocket Protocol

| Event | Direction | Purpose |
|-------|-----------|---------|
| `message:send` | Client → Server | User message to agent |
| `message:stream` | Server → Client | Streaming agent response |
| `agent:status` | Server → Client | Agent status update |
| `task:progress` | Server → Client | Task progress update |

---

## 6. VSCode Adapter

(Already covered in VSCode Extension design)

### Communication Pattern

- Extension host receives messages via VSCode API
- Webview sends/receives via postMessage
- Bridge service handles backend communication

---

## 7. Terminal Adapter

### Modes

**1. Interactive REPL**

```bash
$ maios chat
> Build me a REST API
[Agent-X]: Starting task...
```

**2. One-shot Command**

```bash
$ maios run "Fix the authentication bug"
```

**3. Pipe Mode**

```bash
$ cat error.log | maios analyze
[Agent-Y]: Error analysis: ...
```

### Output Formatting

- Markdown rendering (via rich library)
- Progress bars for long operations
- Syntax highlighting for code blocks

---

## 8. Webhook Adapter

### Endpoints

```
POST /webhooks/{source}
  - /webhooks/github     → GitHub events
  - /webhooks/jira       → Jira events
  - /webhooks/custom     → Generic webhook
```

### GitHub Event Mapping

| GitHub Event | MAIOS Action |
|--------------|--------------|
| `issues.opened` | Create task from issue |
| `pull_request.opened` | Trigger review agent |
| `push` | Run tests via agent |
| `workflow_failed` | Alert agents, investigate |

### Security

- HMAC signature verification
- Configurable secret per webhook source
- Rate limiting per source

### Generic Webhook Format

```json
{
  "source": "custom-system",
  "event_type": "alert",
  "payload": {
    "title": "Build Failed",
    "description": "Production build failed",
    "priority": "high",
    "metadata": {}
  }
}
```

---

## 9. Adapter Manager

### Registry

```python
class AdapterRegistry:
    _adapters: dict[str, BaseAdapter]

    def register(self, adapter_type: str, adapter: BaseAdapter):
        self._adapters[adapter_type] = adapter

    def get(self, adapter_type: str) -> BaseAdapter:
        return self._adapters.get(adapter_type)

    async def broadcast(self, message: OutgoingMessage):
        """Send message to all connected adapters."""
        for adapter in self._adapters.values():
            await adapter.send_message(message)
```

### Router

```python
class AdapterRouter:
    """Routes incoming messages to appropriate handlers."""

    async def route(self, message: IncomingMessage):
        # Determine target agent
        agent_id = await self.resolve_agent(message)

        # Add to message queue
        await self.queue.publish({
            "agent_id": agent_id,
            "message": message
        })
```

---

## 10. Message Queue Integration

### Redis Pub/Sub Channels

| Channel | Purpose |
|---------|---------|
| `maios:incoming` | All incoming messages |
| `maios:outgoing:{adapter}` | Outgoing messages per adapter |
| `maios:events` | System events |

### Message Processing

```python
async def process_messages():
    async for message in redis.subscribe("maios:incoming"):
        # Route to agent runtime
        agent = await get_agent(message.agent_id)
        response = await agent.process(message)

        # Route response back
        await redis.publish(
            f"maios:outgoing:{message.adapter_type}",
            response
        )
```

---

## 11. Configuration

### Environment Variables

```bash
# Slack
SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Discord
DISCORD_ENABLED=false
DISCORD_BOT_TOKEN=...

# Webhook
WEBHOOK_SECRET=...
WEBHOOK_RATE_LIMIT=100  # per hour
```

### Adapter Settings

```python
class AdapterSettings(BaseModel):
    enabled_adapters: list[str] = ["terminal", "web"]
    default_adapter: str = "web"
    streaming_enabled: bool = True
    max_message_length: int = 4000
```

---

*Last updated: 2025-02-12*
