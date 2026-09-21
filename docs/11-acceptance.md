# 11 · Acceptance gates

## Historical P0/P1/P2 retained gates

- Windows/macOS/Linux backend CI stays green.
- Vue type-check, test and production build stay green.
- Stable `asset_id` remains the asset identity.
- Existing asset/search/detail/reference routes remain compatible.
- Legacy SQLite databases upgrade through Alembic without destructive reset.

## P3 search acceptance

- Search covers datasets, fields, metrics, code tables, data standards, word roots and statistical systems.
- Search supports suggestions, highlight output and type/layer/catalog/status facets.
- Search benchmark remains within the agreed local target scale.

Known search/product gaps such as short Chinese terms, multi-token ranking, complete UI pagination and field-level lineage belong to the next functional increment after the trusted-core gate; they are not to be hidden by the P3 seeded corpus.

## P3 relation acceptance

- Multi-level upstream/downstream graph is queryable from a dataset.
- Directed path finding works for reachable and unreachable pairs.
- Downstream impact summary is available.
- Relation navigation resolves back to stable asset detail URLs.

The current table-level relation implementation is retained for compatibility. Correct pure upstream/downstream traversal, the production graph UI and field-level lineage are explicit follow-up work rather than claims of the current implementation.

## Next-P0 trusted-core implementation acceptance

The draft PR must satisfy all of these before the trusted-core increment can be considered complete:

1. `DataControl/agent` remains the owned runtime; startup does not clone or import another Git repository.
2. Portal calls only the local Agent Gateway contract; it does not import Agent3 Core.
3. MCP remains an adapter and contains no duplicated business rules.
4. dsh remains the model/tool loop; Agent3 Core stays harness-agnostic.
5. The untrusted user question is absent from dsh process argv and is supplied through stdin.
6. Resumable session ids are validated before entering the Windows `cmd.exe` launcher path.
7. Gateway SQL output and validation evidence are bound to the same `validate_sql` call id. A later unvalidated SQL must not inherit another SQL's validation state.
8. `thinking`/hidden reasoning is never returned by Gateway/Portal/UI.
9. SQL validity is separate from operation risk and execution permission.
10. Query, DML, DDL and access-control statements may be statically classified; understood mutating statements are not rejected merely because they mutate data.
11. `execution_allowed` remains `false` for every SQL statement class and `sqlExecuted` remains `false` at the runtime boundary.
12. A single `validate_sql` call accepts only one statement, so evidence remains attributable to one program unit.
13. Non-additive snapshot validation rejects predicates such as `dt=A OR dt=B`; a provable single snapshot may pass.
14. Basic CTE/table-alias cases do not treat a CTE name as a physical Portal table; unsupported/unknown semantics fail closed rather than receiving a trusted badge.
15. The intelligent-Q&A UI renders explicit passed/failed/not-validated states, statement type, risk level and readable issue/suggestion text instead of a hard-coded “已校验” badge or raw diagnostic dump.
16. User-visible runtime failures use stable product copy; raw internal diagnostics are not surfaced as the normal UI error message.
17. macOS/Linux has a safe `scripts/stop-dev.sh` counterpart that refuses to kill listeners whose command lines do not match DataControl process markers.

## Deterministic CI gates

CI separates deterministic evidence from real-model evidence.

The cross-platform matrix continues to run:

- Portal Python 3.13 on Windows/macOS/Ubuntu: migration, seeded corpus, Ruff, backend tests and search benchmark;
- Agent Python 3.13 + Node 24 on Windows/macOS/Ubuntu: runtime import, architecture checks, Agent tests, pinned dsh surface, Guard plugin and profile bootstrap;
- Vue on Windows/macOS/Ubuntu: type-check, unit test and production build.

In addition, one Ubuntu `agent-stub-e2e` job runs the scripted DeepSeek Messages stub and proves the full deterministic chain without a real API key:

```text
Portal -> Agent Gateway -> dsh -> Agent3 MCP -> Agent3 Core
```

The stub gate must observe `resolve_metric -> compile_query -> validate_sql`, preserve the requested dimension/latest-period semantics, bind displayed SQL to its validation call, keep execution disabled and demonstrate that shell metacharacters in the question arrive at the model as prompt text instead of process-command text.

A green deterministic stub job is **not** evidence that a real model follows the same tool policy reliably. It only proves the owned integration chain and contracts.

## Local real-model acceptance

This gate is local because model credentials must not be stored in GitHub CI.

With `DEEPSEEK_API_KEY` set before startup, execute `scripts/p3_agent_acceptance.py` with the shared DataControl virtual-environment Python. A passing run must prove:

- unified search, suggestions, relationship graph, path and impact endpoints work against the seeded local environment;
- Portal -> Agent Gateway -> dsh -> MCP -> Agent3 Core succeeds with a real model;
- governed `resolve_metric`, `compile_query` and `validate_sql` calls are observed for the golden question;
- the displayed SQL has `validationState=passed`, `validation.valid=true`, `execution_allowed=false`, and the same `sqlSourceCallId` / `validationCallId`;
- a second dsh process successfully resumes the first persisted `sessionId` and produces the expected regional grouping;
- `sqlExecuted` remains `false` and `hiddenReasoningExposed` remains `false` across original and resumed turns;
- a destructive natural-language request never crosses the product execution boundary. If the model returns a destructive draft instead of refusing, that draft must still be explicitly generation-only and non-executable.

The script writes `.local/p3-agent-acceptance.json` with `acceptanceKind=local-real-model`. `/api/v1/agent/status` may report the runtime as usable before this record exists when all runtime dependencies are healthy, but machine-local `realModelAccepted` / `integrated` only become true after valid local evidence exists.

The committed `agent/runtime-manifest.json` remains conservative (`integrated: false`, `realModelAccepted: false`). Machine-local acceptance evidence and model credentials are never committed.

## Product / visual gate

Source compilation is not visual acceptance. Before PR #4 is merged, the user must manually verify the current target environment and the intelligent-Q&A states against the agreed V2 product direction, including:

- normal answer with governed metric/data-asset evidence;
- SQL static validation passed;
- passed with advisory/risk;
- failed/blocking validation;
- generated but not yet validated SQL;
- friendly runtime error copy;
- no developer-only Gateway/MCP/session debug clutter in the normal product page.

## PR #4 merge gate

PR #4 remains Draft until all of the following are true:

- the final branch head has all deterministic CI jobs green, including `agent-stub-e2e`;
- local real-model acceptance passes on the final accepted head;
- user completes visual/functional acceptance;
- user explicitly approves merging PR #4.

Do not infer merge approval from CI or from a real-model pass.

## Later production concerns

Production database deployment, fine-grained identity/authorization, SSO/LDAP, model-provider hardening, audit/observability, concurrency limits and operational deployment are not part of Next-P0. SSO/LDAP is explicitly deferred from the current five-increment development plan. Field-level lineage, search/product correctness, semantic-model V2 and metadata loading are tracked in subsequent increments rather than being silently folded into this gate.
