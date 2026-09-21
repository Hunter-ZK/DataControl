# 05 · Agent integration V5

## Product rule

DataControl ships the complete product. `DataAgent-dsh` is a pinned migration/provenance source, not an external runtime dependency.

The implemented P3 runtime is:

```text
DataControl Web
  -> Portal FastAPI (:8000, Python 3.13)
  -> Embedded Agent Gateway (:8910, Python 3.14)
  -> dsh `dataagent-headless` session
  -> Agent3 MCP (:8900)
  -> Agent3 Core
  -> Portal read-only HTTP facts
```

No ACP contract is used. The session bridge uses the actual DeepSeek Harness headless surface: one task per process invocation, newline-delimited JSON events, optional `sessionId` continuation, and a terminal `final` event.

## Migration baseline

Source repository: `Hunter-ZK/DataAgent-dsh`

Pinned source commit: `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`

The baseline provides the harness-agnostic Agent3 Core, MCP/HTTP/CLI adapters, dsh assets, Skills, Guard plugin, semantic assets and security/architecture tests. The old `Hunter-ZK/Agent3.0` repository is historical/reference material only.

## Implemented bridge

`agent/src/dataagent_gateway` owns the runtime bridge. It:

1. launches the repository-local pinned `dsh` binary with the `dataagent-headless` profile;
2. passes the user's task to dsh and optionally resumes an existing dsh session;
3. consumes dsh's JSON event stream;
4. projects only session identity, status and Agent3 MCP tool activity to Portal;
5. discards `thinking` and intermediate model-text events;
6. extracts generated SQL / validation evidence when returned by Agent3 tools;
7. never exposes a production SQL execution path.

`dataagent-headless` is bootstrapped from dsh's shipped `headless` profile and receives the same repository patch, model provider, restricted DataAgent preset, Agent3 MCP connection and local Guard plugin as the browser profile.

## Integration rules

1. Required Agent source lives in `DataControl/agent`; application startup never clones another repository.
2. Preserve `dsh/UI/API -> adapters -> Agent3 Core -> domain/ports`.
3. Portal communicates only through the local Agent Gateway and never imports Agent3 Core.
4. Agent3 obtains DataControl facts through the read-only Portal HTTP provider and never opens the Portal database.
5. dsh owns the model loop; Portal owns product UI/session delivery.
6. SQL generation, explanation and validation are allowed; production SQL execution is forbidden.
7. Hidden model reasoning is not returned from the Gateway.
8. The local dsh Guard is defense in depth; network/process isolation remains the deployment boundary.

## Readiness and acceptance

Repository/CI can verify source migration, profile composition, Gateway parsing, MCP boundaries and cross-platform startup without any model secret.

The final P3 real-model gate is intentionally local because `DEEPSEEK_API_KEY` must not enter repository CI. With the key set before startup, run:

```text
scripts/p3_agent_acceptance.py
```

The acceptance verifies:

- Portal -> Gateway -> dsh -> MCP -> Agent3 is reachable;
- a real model calls Agent3 tools;
- generated SQL is captured;
- `validate_sql` is observed;
- SQL is not executed;
- hidden reasoning is not exposed;
- a destructive request does not execute SQL.

A passing run writes `.local/p3-agent-acceptance.json`. Portal status treats that evidence as the real-model gate for the current machine. The committed manifest remains `integrated: false` until user acceptance and P3 merge approval.
