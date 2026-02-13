# MAIOS VSCode Extension Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     VSCODE EXTENSION ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              VSCODE EXTENSION HOST (Node.js)                │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │   │
│  │  │ Commands     │  │ TreeViews    │  │ Status Bar   │       │   │
│  │  │ (maios.*)    │  │ (Agents,     │  │ (Active      │       │   │
│  │  │              │  │  Tasks)      │  │  Project)    │       │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  WEBVIEW PANEL (React App)                           │   │   │
│  │  │                                                       │   │   │
│  │  │  [Agent Network] [Task Board] [Chat] [Config]         │   │   │
│  │  │                                                       │   │   │
│  │  │  Communicates via postMessage() with extension host    │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │  BRIDGE SERVICE (Local HTTP Client)                   │   │   │
│  │  │                                                       │   │   │
│  │  │  - Connects to MAIOS backend (FastAPI :8000)          │   │   │
│  │  │  - Handles WebSocket for realtime updates             │   │   │
│  │  │  - Manages API key authentication                     │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                │
│                                ▼
│                    ┌───────────────────┐
│                    │   MAIOS Backend   │
│                    │   (FastAPI)       │
│                    └───────────────────┘
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Extension Host | TypeScript + VSCode API | Commands, tree views, status bar |
| Webview Panel | React (bundled) | Rich UI inside VSCode |
| Bridge Service | Fetch + WebSocket | Backend communication |

---

## 2. Directory Structure

```
extension/
├── src/
│   ├── extension.ts              # Entry point, activation
│   ├── commands/
│   │   ├── startProject.ts
│   │   ├── showAgents.ts
│   │   └── createAgent.ts
│   ├── providers/
│   │   ├── AgentTreeProvider.ts  # TreeView data provider
│   │   ├── TaskTreeProvider.ts
│   │   └── MaiosWebviewProvider.ts
│   ├── services/
│   │   ├── bridge.ts             # API client
│   │   └── websocket.ts          # Realtime connection
│   └── utils/
│       └── messaging.ts          # Webview communication
├── webview/                       # React app for webview
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── AgentList.tsx
│   │   │   ├── TaskBoard.tsx
│   │   │   └── ChatPanel.tsx
│   │   └── hooks/
│   │       └── useExtension.ts   # VSCode messaging
│   └── package.json
├── package.json                   # Extension manifest
└── tsconfig.json
```

---

## 3. Extension Commands

### Available Commands

| Command | Title | Description |
|---------|-------|-------------|
| `maios.startProject` | MAIOS: Start Project | Create new orchestration project |
| `maios.showAgents` | MAIOS: Show Agents | Open agent panel |
| `maios.showTasks` | MAIOS: Show Tasks | Open task board |
| `maios.createAgent` | MAIOS: Create Agent | Agent creation wizard |
| `maios.runTask` | MAIOS: Run Task | Execute specific task |
| `maios.viewLogs` | MAIOS: View Logs | Show execution logs |
| `maios.connectServer` | MAIOS: Connect Server | Configure backend connection |

### Extension Manifest

```json
{
  "contributes": {
    "commands": [
      { "command": "maios.startProject", "title": "MAIOS: Start Project" },
      { "command": "maios.showAgents", "title": "MAIOS: Show Agents" },
      { "command": "maios.createAgent", "title": "MAIOS: Create Agent" }
    ],
    "viewsContainers": {
      "activitybar": [{
        "id": "maios",
        "title": "MAIOS",
        "icon": "resources/icon.svg"
      }]
    },
    "views": {
      "maios": [
        { "id": "maios.agents", "name": "Agents" },
        { "id": "maios.tasks", "name": "Tasks" }
      ]
    },
    "menus": {
      "editor/context": [
        { "command": "maios.runTask", "when": "editorHasSelection" }
      ]
    }
  }
}
```

---

## 4. Webview Communication

### Message Protocol

```typescript
// Extension → Webview
panel.webview.postMessage({
  type: 'agent:update',
  payload: agent
});

// Webview → Extension
window.addEventListener('message', event => {
  const { type, payload } = event.data;
  if (type === 'task:create') {
    // Handle in extension
  }
});
```

### Message Types

| Direction | Type | Purpose |
|-----------|------|---------|
| Ext → Webview | `agent:list` | Send agent roster |
| Ext → Webview | `agent:update` | Single agent update |
| Ext → Webview | `task:list` | Send task list |
| Ext → Webview | `task:progress` | Task progress update |
| Webview → Ext | `task:create` | Create new task |
| Webview → Ext | `agent:select` | Select agent for detail view |
| Webview → Ext | `config:update` | Update configuration |

---

## 5. Integration Points

### Editor Context Menu

```
┌─────────────────────┐
│ Cut                  │
│ Copy                 │
│ ─────────────────── │
│ MAIOS: Analyze File  │  ← Send file to agent for analysis
│ MAIOS: Add to Task   │  ← Attach file as task context
│ MAIOS: Generate Docs │  ← Agent generates documentation
└─────────────────────┘
```

### Terminal Integration

- "Open in MAIOS Terminal" opens isolated shell
- Agent can read terminal output
- Command history available to agents

### Problems Panel

- Agent-reported issues appear in Problems panel
- Click navigates to relevant code
- Severity levels map to VSCode diagnostic severity

### Source Control

- Agent commits appear in Source Control view
- Review agent changes before accepting
- Diff view for agent modifications

---

## 6. Tree Views

### Agent Tree View

```
MAIOS AGENTS
├── ● Architect-X (Active)
│   └── Task: Design API
├── ○ Dev-Luna (Idle)
└── ● QA-Bot (Active)
    └── Task: Run tests
```

### Task Tree View

```
MAIOS TASKS
├── In Progress (3)
│   ├── #42 Design authentication
│   ├── #43 Implement login
│   └── #45 Write unit tests
├── Pending (5)
│   ├── #46 API documentation
│   └── ...
└── Completed (12)
```

---

## 7. Status Bar Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│ ... editor tabs ...          │ MAIOS: 3 agents active │ Project: API │
└─────────────────────────────────────────────────────────────────────┘
```

Status bar items:
- **Agent Count:** "MAIOS: X agents active"
- **Active Project:** "Project: {name}"
- **Alert Indicator:** Warning icon when escalation pending

---

## 8. Local Bridge Service

### Purpose

When MAIOS backend is not running locally, the extension can start a bridge service.

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  VSCode          │      │  Bridge Service  │      │  MAIOS Backend   │
│  Extension       │─────▶│  (local :3000)   │─────▶│  (cloud/local)   │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

### Bridge Responsibilities

- Authentication token management
- WebSocket connection persistence
- API request proxying
- Local caching for offline support

---

## 9. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Extension | TypeScript | 5.x |
| Extension API | @types/vscode | Latest |
| Bundler | esbuild | Latest |
| Webview | React | 18.x |
| Webview Styling | Tailwind CSS | 3.x |
| HTTP Client | axios | Latest |
| WebSocket | ws | Latest |

---

## 10. Configuration

### Extension Settings

```json
{
  "maios.serverUrl": {
    "type": "string",
    "default": "http://localhost:8000",
    "description": "MAIOS backend server URL"
  },
  "maios.apiKey": {
    "type": "string",
    "default": "",
    "description": "API key for authentication"
  },
  "maios.autoConnect": {
    "type": "boolean",
    "default": true,
    "description": "Automatically connect on VSCode start"
  },
  "maios.notifications": {
    "type": "boolean",
    "default": true,
    "description": "Show MAIOS notifications"
  }
}
```

---

*Last updated: 2025-02-12*
