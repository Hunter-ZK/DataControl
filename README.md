# DataControl

DataControl is a self-contained data-asset service portal and DataAgent product. The repository owns the Vue product UI, FastAPI Portal, search/relationship capabilities, and the DataAgent subsystem under `agent/`.

## Current phase

P2 is frozen on `main`. P3 is developing unified asset search, relationship analysis and intelligent Q&A on `feature/p3-intelligence-relations`.

## Repository architecture

```text
DataControl/
├── web/                 Vue 3 + TypeScript product UI
├── backend/             FastAPI Portal: assets/search/relations/auth/agent gateway
├── agent/               embedded DataAgent subsystem (P3 migration in progress)
├── samples/             synthetic data generators
├── scripts/             Windows/macOS setup, verify and startup helpers
├── docs/                product and architecture decisions
└── .github/             cross-platform CI
```

The final product must not require a second Git repository at runtime. `Hunter-ZK/DataAgent-dsh` is the pinned migration baseline for `agent/`, not a deployed dependency. The old `Hunter-ZK/Agent3.0` repository is historical/reference material only.

## Runtime boundary

```text
Vue
 -> Portal FastAPI
 -> Agent Gateway
 -> DataControl/agent
      -> DeepSeek Harness
      -> MCP Adapter
      -> Agent3 Core
```

Portal and Agent stay isolated by contracts even though they are delivered from one monorepo. Portal never reimplements the agent loop, and Agent3 Core remains independent of Portal/UI protocols.

## Safety boundary

- asset metadata services are read-only to users;
- Agent tools are policy controlled;
- SQL generation and deterministic validation are allowed;
- production SQL execution is outside the current product scope;
- hidden model reasoning is not exposed;
- Agent integration reports not-ready until the embedded runtime has actually migrated and passed end-to-end acceptance.

## Development quick start

### Windows

```powershell
.\scripts\setup-dev.ps1
.\scripts\verify.ps1
.\scripts\start-dev.ps1
```

### macOS / Linux

```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
bash scripts/start-dev.sh
```

Portal API: `http://127.0.0.1:8000`

Vue development UI: `http://127.0.0.1:5173`

P3 Agent startup will be added to the same repository scripts only after the embedded migration gate is satisfied; setup does not clone `DataAgent-dsh` behind the user's back.

## Platform baseline

Portal CI currently runs Python 3.13 on Windows, macOS and Ubuntu. The DataAgent migration source declares Python 3.14, so P3 must explicitly reconcile the runtime version before the Agent gate is opened; the requirement will not be silently weakened.
