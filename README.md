# DataControl

DataControl is a self-contained data-asset service portal and DataAgent product. The repository owns the Vue product UI, FastAPI Portal, search/relationship capabilities, and the DataAgent subsystem under `agent/`.

## Current phase
P2 is frozen on `main`. P3 is developing unified search, relationship analysis and intelligent Q&A on `feature/p3-intelligence-relations`.

The **DataAgent source migration is now complete**. `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96` is the pinned provenance baseline only; DataControl does not clone or import that repository at runtime. The remaining P3 Agent gate is the DataControl-to-dsh session bridge plus real-model end-to-end acceptance.

## Repository architecture
```text
DataControl/
├── web/                 Vue 3 + TypeScript product UI
├── backend/             FastAPI Portal: assets/search/relations/auth/agent gateway
├── agent/               embedded DataAgent: dsh + MCP + Agent3 Core + Skills/Guard
├── samples/             synthetic data generators
├── scripts/             Windows/macOS setup, verify and startup helpers
├── docs/                product and architecture decisions
└── .github/             Portal/Web/Agent cross-platform CI
```

## Runtime boundary
```text
Vue
 -> Portal FastAPI (Python 3.13)
 -> Agent Gateway
 -> DataControl/agent (Python 3.14)
      -> DeepSeek Harness
      -> MCP Adapter
      -> Agent3 Core
      -> Portal read-only HTTP facts
```

Portal and Agent stay isolated by contracts even though they are delivered from one monorepo. Agent3 never imports Portal database models and never opens the Portal database directly.

## Safety boundary
- asset services are read-only to users;
- MCP is a thin adapter, not business Core;
- dsh owns the open-ended agent loop;
- SQL generation/validation are allowed, production SQL execution is not;
- the DuckDB execution backend is evaluation-only and is not an MCP tool;
- hidden model reasoning is not exposed;
- Agent readiness remains closed until a real model + dsh + MCP + Agent3 E2E query passes.

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
Vue UI: `http://127.0.0.1:5173`  
Agent3 MCP (when Python 3.14 Agent env is installed): `http://127.0.0.1:8900/mcp`

If Python 3.14 is not installed, `setup-dev` keeps Portal/Web usable and tells you that Agent setup was skipped. After installing Python 3.14, run `scripts/setup-agent.sh` or `scripts/setup-agent.ps1`; the Agent stays isolated in `.venv-agent`.
