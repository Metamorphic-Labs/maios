# MAIOS MetaContainer Execution Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. MetaContainer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    METACONTAINER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SANDBOX MANAGER                           │   │
│  │  (Docker SDK for Python)                                    │   │
│  │                                                              │   │
│  │  - Container lifecycle (create, start, stop, destroy)       │   │
│  │  - Resource limits (CPU, memory, time)                      │   │
│  │  - Network isolation                                        │   │
│  │  - Volume mounting                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │                                    │
│       ┌────────────────────────┼────────────────────────┐          │
│       │                        │                        │          │
│       ▼                        ▼                        ▼          │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐    │
│  │  EXECUTION  │        │    TEST     │        │   PREVIEW   │    │
│  │ CONTAINER   │        │  CONTAINER  │        │  CONTAINER  │    │
│  │             │        │             │        │             │    │
│  │ Run code    │        │ Run tests   │        │ Serve app   │    │
│  │ snippets    │        │ pytest/jest │        │ for UI      │    │
│  └─────────────┘        └─────────────┘        └─────────────┘    │
│       │                        │                        │          │
│       └────────────────────────┴────────────────────────┘          │
│                                │                                    │
│                                ▼                                    │
│                    ┌───────────────────┐                            │
│                    │  LOG AGGREGATOR   │                            │
│                    │  (Stream to agent │                            │
│                    │   via WebSocket)  │                            │
│                    └───────────────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Container Types

| Type | Image | Purpose | Limits |
|------|-------|---------|--------|
| execution | `python:3.12-slim` | Run Python code snippets | 512MB RAM, 30s timeout |
| node-execution | `node:20-slim` | Run JavaScript/TypeScript | 512MB RAM, 30s timeout |
| test-runner | Custom (project-based) | Run project tests | 2GB RAM, 5min timeout |
| preview | Project-specific | Serve application | 1GB RAM, 30min timeout |

---

## 3. Execution Flow

### Agent → MetaContainer Flow

```
1. AGENT REQUESTS EXECUTION
   agent.call_skill("execute_code", {
     language: "python",
     code: "print('Hello, World!')",
     context_files: ["utils.py"]
   })
                │
                ▼
2. SANDBOX MANAGER CREATES CONTAINER
   - Pull image if not cached
   - Mount context files (read-only)
   - Set resource limits
   - Start container with code injection
                │
                ▼
3. EXECUTION & LOG STREAMING
   Container runs → stdout/stderr captured
                     ↓
   Streamed back to agent via WebSocket
                     ↓
   Agent sees real-time output
                │
                ▼
4. RESULT RETURNED
   {
     "exit_code": 0,
     "stdout": "Hello, World!\n",
     "stderr": "",
     "duration_ms": 45,
     "memory_used_mb": 12
   }
                │
                ▼
5. CONTAINER CLEANUP
   - Container removed
   - Temporary volumes cleaned
   - Resources freed
```

---

## 4. Execution Request/Response Models

### Code Execution

```python
class ExecutionRequest(BaseModel):
    language: Literal["python", "javascript", "typescript"]
    code: str
    context_files: Optional[list[str]] = None
    environment: dict = {}
    timeout_seconds: int = 30

class ExecutionResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    memory_used_mb: float
    error: Optional[str] = None
```

### Test Execution

```python
class TestExecutionRequest(BaseModel):
    project_path: str           # Path to project root
    test_command: str           # e.g., "pytest tests/" or "npm test"
    environment: dict = {}
    timeout_seconds: int = 300

class TestExecutionResult(BaseModel):
    passed: int
    failed: int
    skipped: int
    output: str                 # Full test output
    failures: list[dict]        # Parsed failure details
    coverage: Optional[float]   # If coverage enabled
```

### Preview Mode

```python
class PreviewRequest(BaseModel):
    project_path: str
    command: str                # e.g., "npm run dev"
    port: int = 3000
    environment: dict = {}

class PreviewResult(BaseModel):
    container_id: str
    url: str                    # e.g., "http://localhost:3000"
    status: Literal["starting", "running", "error"]
    logs: str
```

---

## 5. Preview Mode (Frontend Development)

```
Agent: "Let me preview the dashboard component"
       ↓
MetaContainer:
  - Mounts project directory
  - Runs `npm run dev` (or equivalent)
  - Exposes port 3000
  - Proxies to localhost:3000/api → MAIOS backend
       ↓
User sees live preview in:
  - Web UI (iframe)
  - VSCode Webview
  - Direct browser link
       ↓
Agent monitors for errors, suggests fixes
```

---

## 6. Security Model

### Network Isolation

- Containers run in isolated Docker network
- No external network access by default
- Explicit allowlist for package registries:
  - pypi.org
  - npmjs.org

### Resource Limits (per container)

| Resource | Limit |
|----------|-------|
| CPU | 1 core max |
| Memory | 512MB - 2GB (by type) |
| Disk | 1GB temp storage |
| Time | 30s - 5min (by type) |
| PIDs | 100 max processes |

### Filesystem Sandbox

- Read-only mount of project files
- Writable temp directory only
- No access to host filesystem
- No access to MAIOS internals

### Privilege Restrictions

- No `--privileged` flag
- No host PID namespace
- No host network namespace
- Drop all capabilities by default

### Seccomp Profile

Custom seccomp profile blocking:
- Fork bombs
- ptrace
- Mount operations
- Keyring access

---

## 7. Resource Monitoring

```python
class ContainerMetrics(BaseModel):
    container_id: str
    cpu_percent: float
    memory_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    disk_read_bytes: int
    disk_write_bytes: int
    uptime_seconds: int
```

### Monitoring Rules

- Monitoring runs every 1 second
- Alerts sent if:
  - CPU > 90% for 10s
  - Memory > 90% of limit
  - Network activity unexpected

---

## 8. Cleanup Policy

| Scenario | Action |
|----------|--------|
| Normal completion | Remove container immediately |
| Timeout | Kill container, remove, log warning |
| OOM killed | Remove, alert agent, suggest optimization |
| Unexpected error | Remove, capture logs for debugging |
| Preview mode end | Graceful shutdown, then remove |

---

## 9. Log Aggregation

### Log Streaming

```python
async def stream_container_logs(container_id: str) -> AsyncIterator[str]:
    container = docker_client.containers.get(container_id)
    async for line in container.logs(stream=True):
        yield line.decode('utf-8')
```

### Log Delivery

Logs are delivered to agents via:
1. WebSocket streaming (real-time)
2. Redis pub/sub (queued)
3. Database storage (persistent)

### Log Format

```json
{
  "container_id": "...",
  "timestamp": "2025-02-12T10:30:00Z",
  "stream": "stdout",
  "message": "Test passed: test_authentication"
}
```

---

## 10. API Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/api/sandbox/execute` | POST | Execute code snippet |
| `/api/sandbox/test` | POST | Run tests |
| `/api/sandbox/preview` | POST | Start preview container |
| `/api/sandbox/preview/{id}` | GET | Preview status |
| `/api/sandbox/preview/{id}` | DELETE | Stop preview |
| `/api/sandbox/{id}/logs` | GET | Stream logs (WebSocket) |
| `/api/sandbox/{id}/metrics` | GET | Container metrics |

---

## 11. Docker Configuration

### docker-compose.yml Addition

```yaml
services:
  sandbox:
    build:
      context: ./sandbox
      dockerfile: Dockerfile
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./projects:/projects:ro
    environment:
      - SANDBOX_NETWORK=maios_sandbox
      - MAX_CONTAINERS=10
    privileged: false
    security_opt:
      - seccomp:seccomp-profile.json
```

### Sandbox Network

```yaml
networks:
  maios_sandbox:
    driver: bridge
    internal: false  # Allow package registry access
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

---

## 12. Error Handling

### Error Types

| Error | Cause | Agent Action |
|-------|-------|--------------|
| `TIMEOUT` | Execution exceeded time limit | Simplify code, increase timeout |
| `OOM_KILLED` | Memory limit exceeded | Optimize memory usage |
| `NETWORK_ERROR` | Network request failed | Check connectivity, retry |
| `PERMISSION_DENIED` | Missing permission | Request permission or use alternative |
| `SYNTAX_ERROR` | Code has syntax errors | Fix syntax |

### Error Response

```python
class ExecutionError(BaseModel):
    error_type: str
    message: str
    suggestion: str        # Agent-friendly suggestion
    context: dict          # Additional debug info
```

---

*Last updated: 2025-02-12*
