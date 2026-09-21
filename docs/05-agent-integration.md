# 05 · Agent integration V4

## Product rule

DataControl ships the complete product. `DataAgent-dsh` is a migration source, not an external runtime dependency.

The target runtime is:

```text
DataControl Web
  -> Portal FastAPI
  -> local Agent Gateway
  -> DataControl/agent
       -> dsh
       -> MCP Adapter
       -> Agent3 Core
```

No ACP contract is assumed. The P3 implementation must follow the actual interfaces present in the migrated DataAgent baseline rather than inventing a dsh protocol.

## Migration baseline

Source repository: `Hunter-ZK/DataAgent-dsh`

Pinned source commit: `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`

The baseline already provides:

- harness-agnostic `src/agent3` Core;
- MCP / HTTP / CLI adapters;
- DeepSeek Harness profile and restricted query preset;
- domain Skills;
- guard plugin;
- semantic model assets;
- release/architecture/security tests.

The old `Hunter-ZK/Agent3.0` repository is not the P3 runtime target.

## Integration rules

1. Copy/migrate required source assets into `DataControl/agent`; do not clone another repository during application startup.
2. Preserve the dependency direction `dsh/UI/API -> adapters -> Agent3 Core -> domain/ports`.
3. Portal communicates through an Agent Gateway boundary and must not import Agent3 domain modules directly.
4. dsh owns the agent loop; Portal owns UI/session delivery only.
5. SQL may be generated and validated, but DataControl does not execute production SQL.
6. Agent status is explicit. Until migration and local end-to-end validation pass, the UI stays unavailable instead of returning fabricated output.
7. Model/provider settings are configuration owned by the Agent runtime, not hard-coded Portal business logic.

## P3 completion gate

The `agent/runtime-manifest.json` flag may be changed to `integrated: true` only when all are true:

- embedded Agent source is present;
- Windows and macOS setup/start scripts install and launch it from this repository;
- Agent architecture/security tests pass;
- dsh can call the embedded MCP adapter;
- Portal can reach the local Agent Gateway;
- at least one real model + MCP + Agent3 Core query completes without SQL execution;
- repository CI remains green.
