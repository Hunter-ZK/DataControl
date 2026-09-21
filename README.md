# DataControl

DataControl is a self-contained data-asset service portal and DataAgent product. The repository owns the Vue product UI, FastAPI Portal, unified search, relationship analysis and the embedded DataAgent subsystem under `agent/`.

## Current phase
P2 is frozen on `main`. PR #4 on `feature/p3-intelligence-relations` remains a draft while the project completes the first post-P3 hardening increment, **Next-P0: trusted core**.

The branch already contains the P3 code path for unified search, relationship analysis and intelligent Q&A. `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96` is the pinned migration/provenance baseline only; DataControl does not clone or import that repository at runtime.

Next-P0 tightens the contract before merge: untrusted questions cross into dsh through stdin instead of process arguments; displayed SQL is bound to the exact `validate_sql` evidence call; static validation separates SQL correctness from operation risk and execution permission; the intelligent-Q&A UI renders explicit validation states; CI includes a deterministic stub-model full-chain gate in addition to cross-platform unit/build jobs. Real-model and user product acceptance remain separate gates.

## Repository architecture
```text
DataControl/
├── web/                 Vue 3 + TypeScript product UI
├── backend/             FastAPI Portal: assets/search/relations/auth/agent gateway client
├── agent/               embedded DataAgent: dsh + Gateway + MCP + Agent3 Core + Skills/Guard
├── samples/             synthetic data generators
├── scripts/             setup, verification, deterministic/real-model acceptance and startup helpers
├── docs/                product and architecture decisions
└── .github/             Portal/Web/Agent cross-platform CI
```

## Runtime boundary
```text
Vue
 -> Portal FastAPI                    :8000
 -> Embedded Agent Gateway            :8910
 -> dsh headless session
 -> Agent3 MCP                        :8900
 -> Agent3 Core
 -> Portal read-only HTTP facts
```

Portal and Agent run as separate processes and stay isolated by HTTP/MCP contracts, but they share the repository-local `.venv`. The supported Python range is `>=3.13,<3.15`; Python 3.14 is not required. Agent3 never imports Portal database models and never opens the Portal database directly. dsh owns the model loop; MCP remains a thin protocol adapter.

## Current capabilities
- unified search across datasets, fields, metrics, code tables, standards, word roots and statistical systems;
- search suggestions, highlighting and facets;
- multi-hop relationship expansion, directed path lookup and downstream impact analysis;
- DataAgent source embedded in `DataControl/agent`;
- dsh browser and `dataagent-headless` profiles;
- Portal -> Agent Gateway -> dsh -> MCP -> Agent3 Core session path;
- resumable dsh sessions via `sessionId`;
- Agent tool activity, evidence, generated SQL and validation shown without exposing hidden reasoning;
- query/DML/DDL/access-control SQL classified independently from risk, while execution permission remains false;
- deterministic stub-model full-chain acceptance plus a separate local real-model acceptance script.

## Trusted SQL boundary
DataControl treats **validity**, **risk** and **execution** as different concepts.

- Generated SQL may be query, DML, DDL or access-control SQL when the static validator understands the statement class.
- Static validation checks parseability, visible metadata, governed metric semantics and current MaxCompute-specific rules.
- Mutating or destructive statements carry explicit risk/advisory metadata; they are not made invalid merely because they mutate data.
- `execution_allowed` remains `false` for every statement class. DataControl does not execute production SQL.
- DuckDB or other synthetic/desensitized execution is evaluation-only and is not exposed as a production MCP execution tool.
- A SQL card may claim validation only when the displayed SQL and validation result are bound to the same `validate_sql` call.

The current validator improves CTE/alias handling but is not yet a complete MaxCompute semantic compiler. Partition metadata, `MAX_PT` policy and broader statement-specific rules remain later semantic-model work.

## Safety boundary
- the user-facing asset portal is read-only;
- MCP is a thin adapter, not business Core;
- dsh owns the open-ended agent loop;
- untrusted user questions are sent to headless dsh via stdin rather than embedded in its process command arguments;
- SQL generation/validation are allowed, production SQL execution is not;
- hidden model reasoning is discarded at the Gateway and never returned to Portal/UI;
- dsh telemetry, session upload and web tools remain disabled in the current DataAgent profile;
- the Guard plugin is defense in depth, not the sole security boundary.

## Development quick start
The normal setup uses one Python environment for Portal and Agent. Use Python 3.13 or 3.14.

### Windows
```powershell
.\scripts\setup-dev.ps1
$env:DEEPSEEK_API_KEY = "sk-..."   # required only for real Agent queries
.\scripts\start-dev.ps1
```

To stop stale DataControl listeners safely:

```powershell
.\scripts\stop-dev.ps1
```

### macOS / Linux
```bash
bash scripts/setup-dev.sh
export DEEPSEEK_API_KEY="sk-..."    # required only for real Agent queries
bash scripts/start-dev.sh
```

To stop stale DataControl listeners safely:

```bash
bash scripts/stop-dev.sh
```

If Portal/Web are already installed and only Agent dependencies are missing, run `scripts/setup-agent.sh` or `scripts/setup-agent.ps1`; these scripts reuse `.venv` instead of creating a second Python runtime.

Services:
- Portal API: `http://127.0.0.1:8000`
- Vue UI: `http://127.0.0.1:5173`
- Agent3 MCP: `http://127.0.0.1:8900/mcp`
- Embedded Agent Gateway: `http://127.0.0.1:8910`

`start-dev` validates the shared Python runtime and automatically bootstraps missing Agent dependencies/profile before starting the services.

## Verification
Repository-only checks do not require a real model API key:

```powershell
.\scripts\verify.ps1
```

or:

```bash
bash scripts/verify.sh
```

CI also runs `scripts/p0_stub_e2e.py` against `scripts/stub_llm.py` to exercise Portal -> Gateway -> dsh -> MCP -> Agent3 without external model credentials.

For the local real-model gate, start DataControl with `DEEPSEEK_API_KEY` set and then run in another terminal:

```powershell
.\.venv\Scripts\python.exe scripts\p3_agent_acceptance.py
```

or:

```bash
.venv/bin/python scripts/p3_agent_acceptance.py
```

A passing run writes local real-model evidence to `.local/p3-agent-acceptance.json`. The evidence is machine-local and is not a substitute for CI or user visual/functional acceptance.
