# DataControl embedded DataAgent

`agent/` is the self-contained DataAgent subsystem of the DataControl monorepo. Its pinned migration baseline is `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`; that repository is provenance/reference only. DataControl must not need a second Git repository at runtime.

## Embedded assets
- `src/agent3`: harness-agnostic Agent3 Core plus CLI/HTTP/MCP adapters
- `metadata/datacontrol_http.py`: read-only Portal metadata provider; Agent3 never imports Portal DB models
- `.dsh/skills`: query, metric and warehouse workflow skills
- `dsh`: pinned DeepSeek Harness package manifest, restricted preset and profile patch
- `guard-plugin`: fail-closed approval / audit / production-DB defense-in-depth bundle
- `semantic_models`: deterministic public semantic fixture for unit tests
- `tests`: independent Python 3.14 Agent gates

## Runtime boundary
```text
Vue -> Portal FastAPI -> Agent Gateway -> embedded dsh -> MCP -> Agent3 Core
                                              |
                                              +-> Portal read-only HTTP facts
```

The Portal retains Python 3.13. The embedded Agent retains its validated Python 3.14 baseline in `.venv-agent`; the two environments are isolated inside the same repository.

Production SQL execution remains disabled. DuckDB exists only behind the evaluation `ExecutionBackend` and is not registered as an MCP tool.

`runtime-manifest.json` deliberately remains `integrated: false` until the DataControl-to-dsh session bridge and a real model + MCP + Agent3 query are proven end to end.
