# P1 · Backend foundation scope

P1 turns the P0 runnable skeleton into a complete read-only asset-service backend. It does **not** build the full production frontend, relation graph UI or Agent chat experience.

## Scope

1. Complete asset domain models: datasets, columns, tags, standards, code tables/values, word roots, metrics, statistical systems, common SQL, change records and table lineage.
2. Complete read APIs for home overview, catalogs, datasets, columns, standards, metrics/statistical systems and lineage summaries.
3. Application data: local users, favorites and view records; authentication is implemented as a minimal development-ready boundary and will be security-hardened in P4.
4. Stable `asset_id` remains the internal identity for long-lived references.
5. Scheduling remains dataset metadata; no standalone scheduling module.
6. Synthetic data generator is expanded to cover all P1 asset types and relationships.
7. Add backend integration tests for the above contracts.

## Explicitly deferred

- full Vue production implementation (P2)
- relation explorer graph/path UI (P3)
- dsh/Agent3 real conversation integration (P3)
- production SSO/LDAP and full security hardening (P4)
- metadata ingestion/governance workflows
