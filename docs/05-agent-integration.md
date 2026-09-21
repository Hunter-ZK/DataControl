# 05 · Agent integration V6

## Product rule

DataControl ships the complete product. `DataAgent-dsh` is a pinned migration/provenance source, not an external runtime dependency.

The implemented P3 runtime is:

```text
DataControl Web
  -> Portal FastAPI (:8000)
  -> Embedded Agent Gateway (:8910)
  -> dsh `dataagent-headless` session
  -> Agent3 MCP (:8900)
  -> Agent3 Core
  -> Portal read-only HTTP facts
```

Portal and Agent are separate processes with explicit HTTP/MCP contracts, but local development uses one repository-local Python environment. P3 supports Python `>=3.13,<3.15`; Python 3.14 is not a separate runtime requirement.

No ACP contract is used. The session bridge uses the actual DeepSeek Harness headless surface: one task per process invocation, newline-delimited JSON events, optional `sessionId` continuation, and a terminal `final` event.

## Migration baseline

Source repository: `Hunter-ZK/DataAgent-dsh`

Pinned source commit: `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`

The baseline provides the harness-agnostic Agent3 Core, MCP/HTTP/CLI adapters, dsh assets, Skills, Guard plugin, semantic assets and security/architecture tests. Its historical Python 3.14 pin is migration-source metadata, not a DataControl product constraint. The old `Hunter-ZK/Agent3.0` repository is historical/reference material only.

## Implemented bridge

`agent/src/dataagent_gateway` owns the runtime bridge. It:

1. launches the repository-local pinned `dsh` binary with the `dataagent-headless` profile;
2. passes the user's task to dsh and optionally resumes an existing dsh session;
3. consumes dsh's JSON event stream;
4. projects only session identity, status and Agent3 MCP tool activity to Portal;
5. discards `thinking` and intermediate model-text events;
6. extracts generated SQL / validation evidence when returned by Agent3 tools;
7. never exposes a production SQL execution path.

## Web profile versus headless profile

DeepSeek Harness's shipped Web surface supports a per-session Agent Preset roster, so the optional `dataagent` browser profile uses the `dataagent-query` preset.

The shipped Headless runner deliberately does **not** compose that preset roster. `dataagent-headless` therefore uses a separate direct overlay at `agent/dsh/profile/headless.patch.yml` rather than pretending a Web preset exists in headless mode. The overlay:

- sets the DataControl DataAgent persona directly on the headless host Agent;
- forces native tool presentation and disables PTC;
- exposes Agent3 MCP;
- keeps only the read-only DataAgent Skill surface beside MCP;
- pins Skill discovery to `agent/.dsh/skills` and excludes unrelated project/user Skill roots;
- explicitly disables shell, PowerShell, filesystem, job, subagent, workflow, web, todo, goal and plugin-manager model tools;
- applies a read-only permission preset as defense in depth;
- retains the local Guard plugin.

This split is required by the actual dsh runtime contract and is covered by Agent CI tests.

## Integration rules

1. Required Agent source lives in `DataControl/agent`; application startup never clones another repository.
2. Preserve `dsh/UI/API -> adapters -> Agent3 Core -> domain/ports`.
3. Portal communicates only through the local Agent Gateway and never imports Agent3 Core.
4. Agent3 obtains DataControl facts through the read-only Portal HTTP provider and never opens the Portal database.
5. dsh owns the model loop; Portal owns product UI/session delivery.
6. SQL generation, explanation and validation are allowed; production SQL execution is forbidden.
7. Hidden model reasoning is not returned from the Gateway.
8. The local dsh Guard is defense in depth; network/process isolation remains the deployment boundary.
9. Python environment layout is not a security boundary; Portal and Agent may share `.venv` while keeping process/contracts isolated.

## Readiness and acceptance

Repository/CI verifies source migration, the Web and restricted Headless compositions, Gateway event projection, MCP boundaries and cross-platform setup without any model secret. Agent CI executes on Python 3.13 across Windows, macOS and Ubuntu to validate the lower supported runtime boundary.

The final P3 real-model gate is intentionally local because `DEEPSEEK_API_KEY` must not enter repository CI. With the key set **before** starting DataControl, run the repository acceptance script with the shared environment Python:

```bash
.venv/bin/python scripts/p3_agent_acceptance.py
```

On Windows:

```powershell
.\.venv\Scripts\python.exe scripts\p3_agent_acceptance.py
```

The acceptance verifies in one run:

- unified search, suggestions, relationship graph, path and impact endpoints;
- Portal -> Gateway -> dsh -> MCP -> Agent3 real-model reachability;
- a real model calls Agent3 tools;
- generated SQL is captured and `validate_sql` is observed;
- an actual second dsh invocation resumes the first persisted `sessionId`;
- SQL is never executed and hidden reasoning is never exposed;
- a destructive request does not execute SQL.

A passing run writes `.local/p3-agent-acceptance.json`. Portal status only treats local Agent acceptance as complete when the evidence includes a successful session resume plus the SQL/safety invariants. The committed manifest remains conservative (`integrated: false`, `realModelAccepted: false`) until local evidence exists; no secret or machine-specific acceptance result is committed.
