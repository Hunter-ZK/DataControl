# DataControl development guardrails

## Product boundary

DataControl is the complete product repository. `web/`, `backend/` and `agent/` are separate architectural areas inside one monorepo.

## Agent boundary

- `Hunter-ZK/DataAgent-dsh` is the pinned migration baseline for `agent/`; it is not a runtime dependency.
- `Hunter-ZK/Agent3.0` is historical/reference material only.
- Do not add startup logic that clones, imports or shells into another Git repository.
- Portal code may call the local Agent Gateway contract but must not import Agent3 Core directly.
- Agent3 Core must remain harness-agnostic; dsh/MCP/FastAPI belong to adapter/runtime layers.
- Do not invent an ACP or other Harness protocol unless it is verified in the embedded DataAgent implementation.
- SQL generation and validation are permitted; production SQL execution is not.
- Never surface hidden chain-of-thought.

## Change discipline

- Preserve stable `asset_id` identity.
- Keep Windows and macOS behavior equivalent.
- New phase capability must have tests and stay behind an explicit readiness gate until genuinely integrated.
- Do not mark `agent/runtime-manifest.json` as integrated until the P3 acceptance conditions pass.
