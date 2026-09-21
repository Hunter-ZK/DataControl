# 11 · Acceptance gates

## P0/P1/P2 retained gates

- Windows/macOS/Linux backend CI stays green.
- Vue type-check, test and production build stay green.
- Stable `asset_id` remains the asset identity.
- Existing asset/search/detail/reference routes remain compatible.
- Legacy SQLite databases upgrade through Alembic without destructive reset.

## P3 search acceptance

- Search covers datasets, fields, metrics, code tables, data standards, word roots and statistical systems.
- Search supports suggestions, highlight output and type/layer/catalog/status facets.
- Search benchmark remains within the agreed local target scale.

## P3 relation acceptance

- Multi-level upstream/downstream graph is queryable from a dataset.
- Directed path finding works for reachable and unreachable pairs.
- Downstream impact summary is available.
- Relation navigation resolves back to stable asset detail URLs.

## P3 DataAgent implementation acceptance

The repository implementation must satisfy all of these before user acceptance begins:

1. `DataControl/agent` contains the runtime assets migrated from the pinned `DataAgent-dsh` baseline.
2. Runtime startup does not clone or import another Git repository.
3. Portal calls only the local Agent Gateway contract; it does not import Agent3 Core.
4. DataAgent keeps `dsh/UI/API -> adapters -> Agent3 Core -> domain/ports` dependency direction.
5. MCP stays an adapter and contains no duplicated business rules.
6. Portal Python 3.13 and DataAgent Python 3.14 are isolated inside one repository.
7. Windows/macOS/Linux setup, start and verification flows are explicit and fail early when dependencies are missing.
8. The pinned dsh package exposes the `headless` task surface on every CI platform.
9. The browser `dataagent` profile uses the restricted `dataagent-query` preset, while `dataagent-headless` uses a direct restricted host composition because dsh Headless does not compose the Agent Preset roster.
10. Headless exposes Agent3 MCP plus embedded DataAgent Skills, pins Skill discovery to `agent/.dsh/skills`, forces native tool presentation, and explicitly disables general shell/filesystem/job/subagent/workflow/web mutation surfaces.
11. Both dsh profiles load the local Guard plugin and use the DeepSeek provider configuration without retired local-LLM settings.
12. Agent Gateway consumes dsh JSON events and never returns `thinking` events.
13. Session continuation is supported through dsh `sessionId`.
14. SQL execution remains unavailable through the product contract.
15. Portal facts are read by Agent3 only through the read-only HTTP metadata provider.

## P3 real-model acceptance

This gate is local because model credentials must not be stored in GitHub CI.

With `DEEPSEEK_API_KEY` set before startup, execute `scripts/p3_agent_acceptance.py` with the Portal virtual-environment Python. A passing run must prove:

- unified search, suggestions, relationship graph, path and impact endpoints work against the seeded local environment;
- Portal -> Agent Gateway -> dsh -> MCP -> Agent3 Core succeeds with a real model;
- at least one Agent3 MCP tool call is observed;
- generated SQL is captured and `validate_sql` is observed;
- a second dsh process successfully resumes the first persisted `sessionId`;
- `sqlExecuted` remains `false` and `hiddenReasoningExposed` remains `false` across original and resumed turns;
- a destructive request does not execute SQL.

The script writes `.local/p3-agent-acceptance.json`. `/api/v1/agent/status` may report the runtime as usable before this record exists when all runtime dependencies are healthy, but machine-local `realModelAccepted` / `integrated` only become true after the evidence includes successful session resumption plus the SQL/safety invariants.

The committed `agent/runtime-manifest.json` remains conservative (`integrated: false`, `realModelAccepted: false`). Machine-local acceptance evidence and model credentials are never committed.

## P3 merge gate

- all 9 cross-platform CI jobs green on the final P3 head;
- local real-model acceptance passed;
- user validates the P3 product on the target environment;
- user explicitly approves merging PR #4.

## P4 production acceptance

SSO/LDAP, production DB deployment, fine-grained security, audit/observability, caching and operational deployment are P4 concerns and are not prerequisites for P3 functional acceptance unless they become necessary to close a security boundary.
