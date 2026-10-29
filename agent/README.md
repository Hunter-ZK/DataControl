# DataControl embedded DataAgent

`agent/` is the self-contained DataAgent subsystem of the DataControl monorepo. Its pinned migration baseline is `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`; that repository is provenance/reference only. DataControl must not need a second Git repository at runtime.

## Embedded assets
- `src/agent3`: harness-agnostic Agent3 Core plus CLI/HTTP/MCP adapters
- `src/dataagent_gateway`: headless dsh HTTP gateway owned by DataControl
- `metadata/datacontrol_http.py`: read-only Portal metadata provider; Agent3 never imports Portal DB models
- `.dsh/skills`: query, metric and warehouse workflow skills
- `dsh`: pinned DeepSeek Harness package manifest, restricted preset and profile patch
- `guard-plugin`: fail-closed approval / audit / production-DB defense-in-depth bundle
- `semantic_models`: deterministic public semantic fixture for unit tests
- `tests`: independent Agent gates executed on the shared Python 3.13 baseline

## Runtime boundary
```text
Vue
 -> Portal FastAPI (:8000)
 -> Embedded Agent Gateway (:8910)
 -> dsh dataagent-headless session
 -> Agent3 MCP (:8900)
 -> Agent3 Core
 -> Portal read-only HTTP facts
```

Portal and Agent run as separate processes and remain isolated by HTTP/MCP contracts, but they use the same repository-local `.venv`. The supported P3 Python range is `>=3.13,<3.15`; no separate `.venv-agent` or Python 3.14-only installation is required.

The gateway launches one dsh headless task per Portal request and uses the dsh JSON event stream for session identity, tool activity, final answer and stop reason. `thinking` events and intermediate model text are intentionally discarded. Only Agent3 MCP tool activity is projected back to the product.

`dataagent-headless` is bootstrapped from the shipped dsh `headless` profile and receives the DataAgent patch, MCP connection, local Guard plugin, model provider and restricted DataAgent skill surface.

Production SQL execution remains disabled. DuckDB exists only behind the evaluation `ExecutionBackend` and is not registered as an MCP tool.

## P3 gate
`runtime-manifest.json` records that source migration and the session bridge are implemented. Repository/CI checks can verify the architecture without a model key. The manifest stays `integrated: false` until a user-owned real `DEEPSEEK_API_KEY` completes `scripts/p3_agent_acceptance.py` and product acceptance.

A successful local acceptance writes `.local/p3-agent-acceptance.json`; Portal status treats that local evidence as the real-model gate for the current machine without committing credentials or machine-specific evidence to Git.

## Local developer autonomy and runtime upgrade (2026-10-27)

- Pinned dsh: `@deepseek-ai/dsh@0.2.1-rc.3`. A separate default home at
  `.local/dsh-home-v0.2.1-rc.3` leaves the previous `.local/dsh-home` intact for rollback.
- The optional Harness Web debugger now uses the v0.2.1 declarative
  `agent-preset-registry` and the shipped `standard` preset; the old
  file-based `dataagent-query` directory is retained only as migration history.
- The headless profile exposes Goal / Todo / subagents / workflow / Plan Mode
  integration and compaction. Model-driven multi-step planning works without
  requiring the interactive Plan Mode approval UI; do not enter interactive
  plan-review mode from the headless API until a user-question channel exists.
- The development runtime remains **read-only** with Agent3 MCP as its only
  business tool surface. Shell, file mutation, public Web, production SQL execution
  and DDL submission remain unavailable. Auto-planning is not blanket execution permission.
- On Windows: `./scripts/setup-agent.ps1` then `./scripts/start-dev.ps1`.
  On macOS/Linux: `bash scripts/setup-agent.sh` then `bash scripts/start-dev.sh`.
- A real `DEEPSEEK_API_KEY` is needed for actual model acceptance. CI stub
  coverage cannot certify model behavior; run `python scripts/p3_agent_acceptance.py`
  locally with a running 8000/8900/8910 stack.
- Rollback: select the previous branch and rerun setup; the old pinned package
  and old DSH home remain separate. Never run a test on irreplaceable sessions.


## Optional public-model test lane

Windows users may opt in to `Ebony-Vinyl/dsh-our-free-model@v2.7.2` via
`scripts/setup-free-model-test.ps1` and `scripts/start-free-test.ps1`.
It runs in an independent read-only profile, not the official default.
See `docs/free-model-local-test.md`; never send non-synthetic metadata to public providers.
