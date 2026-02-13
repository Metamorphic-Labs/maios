# MAIOS Frontend & Visualization Design

**Version:** 1.0 | **Date:** 2025-02-12 | **Status:** Approved

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS 15 APP ROUTER                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Layout    │  │   Pages     │  │    API      │  │  Server    │ │
│  │ (Root +     │  │ (Dashboard, │  │  Routes     │  │  Actions   │ │
│  │  Agents)    │  │  Projects)  │  │  (/api/*)   │  │            │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                         CLIENT COMPONENTS                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 3D Canvas    │  │  Dashboard   │  │  Agent       │              │
│  │ (R3F/Three)  │  │  Widgets     │  │  Panels      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│                         STATE & REALTIME                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Zustand      │  │ React Query  │  │ WebSocket    │              │
│  │ (Client UI)  │  │ (Server)     │  │ (Live)       │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────┐
                    │   MAIOS Backend   │
                    │   (FastAPI)       │
                    └───────────────────┘
```

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| App Router (not Pages) | RSC support, streaming, modern patterns |
| Zustand for client state | Lighter than Redux, better for 3D performance |
| React Query for server state | Automatic caching, refetch, optimistic updates |
| Native WebSocket | Lighter than Socket.io for this use case |

---

## 2. Directory Structure

```
frontend/
├── app/
│   ├── (dashboard)/              # Dashboard layout group
│   │   ├── layout.tsx            # Dashboard shell
│   │   ├── page.tsx              # Main dashboard
│   │   ├── projects/
│   │   │   ├── page.tsx          # Project list
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # Project detail
│   │   │       └── components/
│   │   │           ├── TaskBoard.tsx
│   │   │           └── Timeline.tsx
│   │   └── agents/
│   │       ├── page.tsx          # Agent roster
│   │       └── [id]/
│   │           └── page.tsx      # Agent detail
│   ├── (immersive)/              # Full 3D immersive view
│   │   └── neural/
│   │       └── page.tsx          # Neural graph view
│   └── api/
│       └── trpc/                 # tRPC routes (optional)
├── components/
│   ├── ui/                       # ShadCN primitives
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── ...
│   ├── agents/
│   │   ├── AgentCard.tsx
│   │   ├── AgentStatusOrb.tsx
│   │   ├── AgentPanel.tsx
│   │   └── AgentCreator.tsx
│   ├── tasks/
│   │   ├── TaskBoard.tsx         # Kanban-style
│   │   ├── TaskCard.tsx
│   │   └── TaskPipeline.tsx      # Animated flow
│   ├── visualization/
│   │   ├── NeuralGraph.tsx       # 3D agent network
│   │   ├── TaskFlow.tsx          # 3D task animation
│   │   └── PerformanceHeatmap.tsx
│   └── layout/
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── CommandPalette.tsx
├── hooks/
│   ├── useWebSocket.ts
│   ├── useAgentStream.ts
│   └── useProject.ts
├── stores/
│   ├── useUIStore.ts             # Zustand
│   └── useAgentStore.ts
└── lib/
    ├── api-client.ts
    └── websocket.ts
```

---

## 3. 3D Visualization Architecture

Using **React Three Fiber (R3F)** as the React renderer for Three.js.

### Scene Structure

```
<Canvas> (R3F)
├── <OrbitControls> - Camera navigation
├── <Environment> - Subtle ambient lighting
├── <PostProcessing> - Bloom, subtle glow
├── <NeuralGraph>
│   ├── <AgentNode> × N (positioned in 3D space)
│   │   ├── StatusOrb (pulsing glow)
│   │   ├── RoleLabel (floating text)
│   │   └── PerformanceRing (score visualization)
│   ├── <ConnectionLine> × M (between agents/teams)
│   │   ├── Animated particles for active tasks
│   │   └── Color-coded by task type
│   └── <TeamCluster> (grouped nodes)
│       ├── Enclosing sphere/hull
│       └── Team pulse effect
└── <TaskFlow> (optional layer)
    ├── <TaskParticle> flowing along edges
    └── <StatusBeam> from Orchestrator
```

### Visual Elements

| Element | Behavior | Implementation |
|---------|----------|----------------|
| Agent Node | Sphere with glow intensity based on activity | `<mesh>` + emissive material |
| Status Orb | Pulsing animation (idle=slow, active=fast) | `useFrame` hook with sin wave |
| Connection Lines | Bezier curves between nodes | `<QuadraticBezierLine>` from drei |
| Task Particles | Animated dots flowing along connections | InstancedMesh + shader |
| Team Cluster | Semi-transparent hull around team members | ConvexGeometry + wireframe |
| Orchestrator | Central node with radiating beams | Larger mesh + ray effect |

### Interaction

- **Click agent node** → slide-in detail panel
- **Hover** → glow intensify + tooltip
- **Drag** → reposition (positions saved to localStorage)
- **Double-click** → zoom and focus

### Performance

- InstancedMesh for particles (not individual meshes)
- Frustum culling enabled
- LOD (Level of Detail) for distant nodes
- Maximum 200 agents visible at once (pagination for larger orgs)

---

## 4. State Management

### Server State (React Query)

```typescript
useQuery(['projects'])     // Project list
useQuery(['agents'])       // Agent roster
useQuery(['project', id])  // Project detail + tasks
useMutation(...)           // Create/update operations
```

Cache invalidation triggered by:
- WebSocket events
- Manual refetch
- Optimistic updates

### Client State (Zustand)

```typescript
// useUIStore
interface UIStore {
  sidebarOpen: boolean;
  selectedAgentId: string | null;
  viewMode: 'dashboard' | 'neural' | 'timeline';
  commandPaletteOpen: boolean;
}

// useVisualizationStore
interface VisualizationStore {
  cameraPosition: [number, number, number];
  nodePositions: Map<string, Position>;
  highlightedConnections: string[];
}
```

### Real-time Updates (WebSocket)

**Connection:** `ws://localhost:8000/ws`

**Event Types:**

| Event | Purpose |
|-------|---------|
| `agent:status` | Agent busy/idle/error |
| `task:created` | New task spawned |
| `task:progress` | Task update (percentage, message) |
| `task:completed` | Task finished |
| `project:updated` | Project state change |
| `negotiation:start` | Agent debate begins |
| `escalation:created` | Issue needs attention |

**Message Format:**

```json
{
  "type": "task:progress",
  "payload": { "taskId": "...", "percent": 45, "message": "..." }
}
```

---

## 5. UI Components & Brand Integration

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER (--surface-1, --line-1 border)                             │
│  [Logo]          [Project Selector]    [Agent Status]  [⚙]         │
├───────────┬─────────────────────────────────────────────────────────┤
│ SIDEBAR   │                    MAIN                                  │
│           │  ┌────────────────────────────────────────────────────┐ │
│ Dashboard │  │  3D CANVAS (or Dashboard view)                     │ │
│ Projects  │  │                                                    │ │
│ Agents    │  │  [Agent Nodes] [Connections] [Particles]           │ │
│ Teams     │  │                                                    │ │
│ Memory    │  └────────────────────────────────────────────────────┘ │
│ Settings  │  ┌────────────────────────────────────────────────────┐ │
│           │  │  TASK BOARD (Kanban)                               │ │
│           │  │  [Backlog] [In Progress] [Review] [Done]           │ │
│           │  └────────────────────────────────────────────────────┘ │
├───────────┴─────────────────────────────────────────────────────────┤
│  ACTIVITY FEED (--surface-1)                                        │
│  [timestamp] Agent-X completed task #42                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Brand Tokens

| Component | Brand Tokens | Behavior |
|-----------|--------------|----------|
| AgentCard | `--surface-1`, `--line-1` | Card with status orb, role, score, current task |
| TaskCard | `--surface-2`, `--line-1` | Draggable kanban card with priority indicator |
| StatusOrb | `--brand-primary` glow | Pulsing sphere, color shifts by status |
| Badge | `--surface-2`, `--brand-primary` text | Role/skill tags |
| Button (primary) | `--brand-primary` bg | With glow on hover |
| Button (secondary) | `--surface-2`, `--line-1` | Subtle, low emphasis |
| Input | `--surface-2`, `--fg` | Focus ring `--brand-primary` |

### Motion Guidelines

From BRANDING.md:
- Duration: 150-200ms
- Easing: `cubic-bezier(0.2, 0.8, 0.2, 1)`
- Glow pulse: `--glow-primary` at varying opacity

---

## 6. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js | 15.x (App Router) |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | 4.x |
| UI Components | ShadCN UI | Latest |
| 3D Graphics | React Three Fiber | 8.x |
| 3D Helpers | @react-three/drei | 9.x |
| Client State | Zustand | 4.x |
| Server State | @tanstack/react-query | 5.x |
| Animation | Framer Motion | 11.x |
| Forms | React Hook Form | 7.x |
| Validation | Zod | 3.x |

---

## 7. API Integration

### REST Endpoints (from Phase 1)

| Path | Method | Purpose |
|------|--------|---------|
| `/api/projects` | POST | Create project |
| `/api/projects/{id}` | GET | Project details |
| `/api/projects/{id}/input` | POST | Human input |
| `/api/agents` | GET/POST | List/create agents |
| `/api/tasks` | GET | List tasks |
| `/api/memory/search` | POST | Search knowledge |

### WebSocket Endpoints

| Path | Purpose |
|------|---------|
| `/ws` | Global event stream |
| `/ws/project/{id}` | Project-specific events |

---

*Last updated: 2025-02-12*
