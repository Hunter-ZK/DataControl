# 01 · Architecture V4

DataControl is the complete product repository. Portal and DataAgent keep strict module/runtime boundaries, but both are owned and shipped from `Hunter-ZK/DataControl`.

```text
                           DataControl monorepo
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│  Vue 3 Web                                                    │
│      │                                                        │
│      v                                                        │
│  FastAPI Portal ---- asset/application store                  │
│      │            \\ SQLite demo/CI; MySQL production target  │
│      │                                                        │
│      ├── Asset / Search / Standard / Relation / User          │
│      │                                                        │
│      └── Agent Gateway                                        │
│              │                                                │
│              v                                                │
│          agent/ local DataAgent runtime                       │
│              │                                                │
│              ├── DeepSeek Harness (replaceable Agent Runtime) │
│              │        │                                       │
│              │        v MCP                                   │
│              └── Agent3 Adapter -> Agent3 Core                │
│                                  ├── Metadata                 │
│                                  ├── Semantic                 │
│                                  └── SQL / Policy             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Repository boundary

1. `DataControl` is self-contained. Deployment must not require cloning `DataAgent-dsh` or `Agent3.0`.
2. `DataAgent-dsh` is the P3 migration baseline for `agent/`, pinned at commit `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`.
3. `Agent3.0` is historical/reference material, not the runtime integration target.
4. Portal and Agent remain separately testable. Sharing a repository does not permit uncontrolled cross-imports.

## Frozen ownership

1. Stable asset identity is `asset_id`; names are mutable attributes.
2. Portal owns asset facts, identity, search, relations, users, audit and product/session delivery.
3. DataAgent owns dsh workflow, skills, semantic/SQL intelligence, deterministic validation and Agent3 Core.
4. dsh owns the open-ended model loop. Portal must not build a second agent loop.
5. MCP/HTTP/CLI are protocol adapters only; business rules stay in Agent3 Core.
6. Production SQL execution remains disabled in the DataControl V1/P3 product boundary.
7. Hidden chain-of-thought is not exposed.

## Portal-Agent seam

The Portal talks only to the local Agent Gateway contract. The concrete dsh/MCP internals remain behind `agent/`. This prevents the Web/Portal from depending on dsh protocol details and allows the Agent runtime to evolve without rewriting product pages.

During P3 migration the Agent Gateway reports not-ready until the embedded Agent source, startup scripts, tests and end-to-end runtime all pass. A disabled capability is preferred to a fake integration.

## Search ADR

Use the embedded SQLite FTS5 trigram index behind the `SearchEngine` boundary for the current target scale. P3 adds unified asset indexing, suggestions and facets without coupling the Portal to an external search service.
