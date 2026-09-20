# 11 · Acceptance

## P2 automated acceptance

Run the platform-specific verification script after setup.

Windows:
```powershell
.\scripts\setup-dev.ps1
.\scripts\verify.ps1
```

macOS:
```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
```

The verification gate covers:
- Alembic migration
- deterministic demo/P1 enrichment data
- Ruff
- backend pytest
- search benchmark
- Vue/TypeScript type-check
- Vitest
- Vite production build

The final line must be `P2 VERIFICATION PASSED`.

## Cross-platform CI

Both Python and frontend jobs must pass on:
- Windows
- macOS
- Ubuntu

## P2 functional acceptance

1. `/health` reports phase `P2`.
2. Home is a search portal, not an asset dashboard.
3. Main navigation uses the light-ocean product shell and real SVG icons.
4. Search submission opens `/search?q=...`; search results can open dataset, field, metric and code-table destinations.
5. Asset catalog supports business-directory filtering and keyword lookup.
6. Dataset detail contains business definition, field list, common SQL, changes, lineage summary and `调度与运行` within the dataset page.
7. Field detail is independently routable and linked from the dataset field table.
8. Code tables and data standards have list/detail navigation; word roots, metrics and statistical systems have detail routes.
9. Data Overview is a separate page.
10. Personal Center exposes favorites, recent views and search history after development login.
11. Browser forward/back and direct routes work through Vue Router; built SPA routes can be served by FastAPI history fallback.
12. The layout remains centered and usable at 1920, 1440, 1280, 1024, 820 and narrow mobile-like browser widths without page-level horizontal overflow.
13. Sidebar behaviour: full navigation -> icon rail -> hidden navigation as viewport width decreases.
14. Technical names never widen the page; tables scroll internally when necessary.
15. Windows and macOS use the same product capability and validation data.

## Visual acceptance focus

P2 design direction is `Light Ocean × Calm SaaS × Data Tool`:
- very light ocean/blue-grey navigation
- white reading surfaces
- blue reserved for actions/selection/links rather than large saturated panels
- restrained shadows and gradients
- consistent radius, spacing and type hierarchy
- low-contrast chrome so asset content remains the visual focus
- professional vector icons instead of prototype Unicode glyphs

## Deferred acceptance

Not P2 gates:
- full relationship graph/path/impact explorer
- production advanced search ranking/facet service
- real dsh + Agent3 conversation
- SQL execution
- production SSO/LDAP
- admin/operations console
- metadata ingestion/governance
