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
- `tests`: independent Python 3.14 Agent gates

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

The Portal retains Python 3.13. The embedded Agent retains its validated Python 3.14 baseline in `.venv-agent`; the two environments are isolated inside the same repository.

The gateway launches one dsh headless task per Portal request and uses the dsh JSON event stream for session identity, tool activity, final answer and stop reason. `thinking` events and intermediate model text are intentionally discarded. Only Agent3 MCP tool activity is projected back to the product.

`dataagent-headless` is bootstrapped from the shipped dsh `headless` profile and receives the same DataAgent patch, MCP connection, local Guard plugin, model provider and restricted DataAgent preset as the browser profile.

Production SQL execution remains disabled. DuckDB exists only behind the evaluation `ExecutionBackend` and is not registered as an MCP tool.

## P3 gate
`runtime-manifest.json` records that source migration and the session bridge are implemented. Repository/CI checks can fully verify the architecture without a model key. The manifest stays `integrated: false` until a user-owned real `DEEPSEEK_API_KEY` completes `scripts/p3_agent_acceptance.py` and product acceptance.

A successful local acceptance writes `.local/p3-agent-acceptance.json`; Portal status treats that local evidence as the real-model gate for the current machine without committing credentials or machine-specific evidence to Git.
