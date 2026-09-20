# P1 · Backend foundation scope

P1 turns the P0 runnable skeleton into a complete read-only asset-service backend. It does **not** build the full production frontend, relation graph UI or Agent chat experience.

## Completed scope

1. Complete asset domain models: datasets, columns, tags, standards, code tables/values, word roots, metrics, statistical systems, common SQL, change records and table lineage.
2. Complete read APIs for home overview, catalogs, datasets, columns, standards, metrics/statistical systems, common SQL, changes, tags and lineage summaries.
3. Application data: local users, favorites, view records, search history and audit logs.
4. Minimal development-ready authentication boundary with signed expiring bearer tokens; production hardening remains P4.
5. Stable `asset_id` remains the internal identity for long-lived references.
6. Scheduling remains dataset metadata; no standalone scheduling module.
7. Synthetic data covers all P1 asset/application types and relationships.
8. Alembic baseline migration added for schema initialization.
9. Backend integration tests cover auth, activity, detail/reference APIs and search.
10. Windows/macOS development scripts and CI verification are maintained in parallel.

## UI corrections folded into the P1 verification branch

The P1 branch also includes the latest P0 UI corrections required for validation:
- dedicated full search results page after search/suggestion selection;
- search layout simplified to filters + result list, removing the misplaced third-side tips panel;
- global `aside` CSS collision removed by scoping the application sidebar explicitly;
- return controls added to search, overview and detail pages, plus top-bar back navigation;
- responsive breakpoints for wide desktop, compact desktop and narrow browser widths;
- lighter ocean-blue sidebar palette.

## Explicitly deferred

- full Vue production implementation (P2)
- relation explorer graph/path UI (P3)
- dsh/Agent3 real conversation integration (P3)
- production SSO/LDAP and full security hardening (P4)
- metadata ingestion/governance workflows

## P1 acceptance command

Windows:

```powershell
.\scripts\verify.ps1
```

macOS:

```bash
bash scripts/verify.sh
```

A successful run ends with `P1 VERIFICATION PASSED`.
