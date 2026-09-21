# DataControl

DataControl is a self-contained data-asset service portal and DataAgent product. The repository owns the Vue product UI, FastAPI Portal, unified search, relationship analysis and the embedded DataAgent subsystem under `agent/`.

## Current phase
P2 is frozen on `main`. P3 is a release candidate on `feature/p3-intelligence-relations`.

P3 now contains the full code path for unified search, relationship analysis and intelligent Q&A. `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96` is the pinned migration/provenance baseline only; DataControl does not clone or import that repository at runtime. The only remaining release gate is local real-model acceptance with the user's own DeepSeek API key, followed by product acceptance before merge.

## Repository architecture
```text
DataControl/
├── web/                 Vue 3 + TypeScript product UI
├── backend/             FastAPI Portal: assets/search/relations/auth/agent gateway client
├── agent/               embedded DataAgent: dsh + Gateway + MCP + Agent3 Core + Skills/Guard
├── samples/             synthetic data generators
├── scripts/             Windows/macOS setup, verification, acceptance and startup helpers
├── docs/                product and architecture decisions
└── .github/             Portal/Web/Agent cross-platform CI
```

## Runtime boundary
```text
Vue
 -> Portal FastAPI                    :8000  (Python 3.13)
 -> Embedded Agent Gateway            :8910  (Python 3.14)
 -> dsh headless session
 -> Agent3 MCP                        :8900
 -> Agent3 Core
 -> Portal read-only HTTP facts
```

Portal and Agent stay isolated by contracts even though they are delivered from one monorepo. Agent3 never imports Portal database models and never opens the Portal database directly. dsh owns the model loop; MCP remains a thin protocol adapter.

## P3 capabilities
- unified search across datasets, fields, metrics, code tables, standards, word roots and statistical systems;
- search suggestions, highlighting and facets;
- multi-hop relationship expansion, directed path lookup and downstream impact analysis;
- DataAgent source embedded in `DataControl/agent`;
- dsh browser and `dataagent-headless` profiles;
- Portal -> Agent Gateway -> dsh -> MCP -> Agent3 Core session path;
- resumable dsh sessions via `sessionId`;
- Agent tool activity, generated SQL and validation shown in the UI without exposing hidden reasoning;
- real-model acceptance script that verifies MCP use, SQL validation, no SQL execution and destructive-request safety.

## Safety boundary
- asset services are read-only to users;
- MCP is a thin adapter, not business Core;
- dsh owns the open-ended agent loop;
- SQL generation/validation are allowed, production SQL execution is not;
- the DuckDB execution backend is evaluation-only and is not an MCP tool;
- hidden model reasoning is discarded at the Gateway and never returned to Portal/UI;
- dsh telemetry, session upload and web tools remain disabled in the DataAgent profile;
- the Guard plugin is defense in depth, not the sole security boundary.

## Development quick start
### Windows
```powershell
.\scripts\setup-dev.ps1
$env:DEEPSEEK_API_KEY = "sk-..."   # required only for real Agent queries
.\scripts\start-dev.ps1
```

### macOS / Linux
```bash
bash scripts/setup-dev.sh
export DEEPSEEK_API_KEY="sk-..."    # required only for real Agent queries
bash scripts/start-dev.sh
```

Services:
- Portal API: `http://127.0.0.1:8000`
- Vue UI: `http://127.0.0.1:5173`
- Agent3 MCP: `http://127.0.0.1:8900/mcp`
- Embedded Agent Gateway: `http://127.0.0.1:8910`

If Python 3.14 is not installed, `setup-dev` keeps Portal/Web usable and tells you that Agent setup was skipped. After installing Python 3.14, run `scripts/setup-agent.sh` or `scripts/setup-agent.ps1`; the Agent stays isolated in `.venv-agent`.

`start-dev` now fails early with an actionable message when frontend dependencies, dsh dependencies or the headless profile are missing instead of surfacing a late `vite`/runtime command error.

## Verification
Repository-only checks do not require an API key:

```powershell
.\scripts\verify.ps1
```

or:

```bash
bash scripts/verify.sh
```

For the final P3 real-model acceptance, start DataControl with `DEEPSEEK_API_KEY` set and then run in another terminal:

```powershell
.\.venv\Scripts\python.exe scripts\p3_agent_acceptance.py
```

or:

```bash
.venv/bin/python scripts/p3_agent_acceptance.py
```

A passing run writes local evidence to `.local/p3-agent-acceptance.json`. That file is ignored by Git and is used only to surface local acceptance state in the product status panel.
