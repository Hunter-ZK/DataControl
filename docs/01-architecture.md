# 01 · Architecture V3

```text
Vue 3 / prototype UI
        |
        v
FastAPI portal backend ---- MySQL 8 (production asset/application store)
        |                  \\ SQLite permitted for self-contained demo/CI
        |-- embedded search index (P0 choice: SQLite FTS5 trigram)
        |
        | ACP stdio
        v
       dsh ---- model provider (DeepSeek/Qwen/future internal endpoint)
        |
        | MCP HTTP
        v
     Agent3 Core
        |
        | internal read-only HTTP
        +----> FastAPI portal backend
```

## Frozen boundaries
1. Stable asset identity is `asset_id`; names are mutable attributes.
2. Portal owns asset facts, identity, search, relations, users and audit.
3. Agent3 owns SQL intelligence and deterministic semantic compilation, not persistence.
4. dsh owns the agent loop. No custom agent loop in the portal.
5. Agent3 does not access the database directly.
6. No SQL execution.

## Search ADR (P0)
Use an embedded SQLite FTS5 trigram index behind a `SearchEngine` boundary. It has zero extra service dependencies, supports Chinese substring search and technical identifiers, BM25 ranking and highlighting. Advanced typo handling/faceting can be layered in P3 without changing the public search service contract. Re-evaluate external search only if P3 benchmark fails the target scale.
