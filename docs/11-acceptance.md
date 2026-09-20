# 11 · Acceptance

## P1 automated acceptance

Run the platform-specific verification script.

Windows:

```powershell
.\scripts\verify.ps1
```

macOS:

```bash
bash scripts/verify.sh
```

The script verifies:
- Alembic baseline migration
- deterministic P0/P1 synthetic data generation
- Ruff static checks
- backend API/integration tests
- search benchmark
- UI layout contract: one shell grid, bounded centered content, two-column search structure, return controls and responsive breakpoints

The final line must be `P1 VERIFICATION PASSED`.

## P1 functional acceptance

1. `/health` returns phase `P1`.
2. `/docs` exposes dataset, field, reference, auth and activity APIs.
3. Local demo login succeeds for the generated demo accounts.
4. Dataset/column/catalog/code table/data standard/word root/metric/statistical-system APIs return seeded data.
5. Dataset tags, changes, common SQL and upstream/downstream summaries are queryable.
6. Favorites, views, search history and admin audit records can be read/written through the API boundary.
7. Search home suggestions lead to a dedicated result page.
8. Search result layout contains only **filter + result** regions. No independent right-side tips panel or “更好地找到资产” panel exists.
9. Search, overview and dataset detail pages have explicit return controls and top-bar back navigation.
10. All primary pages use a common centered `content-container`; cards must not anchor to the left edge on wide screens.
11. No page-level layout uses `margin-left + calc(width)` to compensate for a fixed sidebar. The outer application uses one CSS Grid shell and every content column uses `minmax(0, 1fr)` / `min-width: 0` to prevent overflow.
12. Responsive validation must cover at least these viewport widths:
   - 1920px: centered bounded content, full 224px sidebar, no stretched panels
   - 1440px: centered bounded content, no horizontal overflow
   - 1280px: compact layout remains aligned; home cards reflow
   - 1024px: sidebar collapses to icon rail; search filter becomes an inline filter row above results
   - 820px: content becomes single-column and remains full-width inside page padding
   - 560px: cards, stats, metadata and search results become single-column; tables scroll inside their own container only
13. Long technical names may truncate/wrap inside their own component but must never widen the page.
14. Windows and macOS setup/start/verify scripts both exist and CI runs Windows/macOS/Linux.
15. The prototype HTML disables stale-shell caching and CSS/JS URLs use a revision query string so a pull/restart cannot silently display the previous layout.

## Deferred acceptance

The following are not P1 gates: full Vue production UI, relation graph/path explorer, real dsh/Agent3 conversation, production SSO/LDAP, metadata ingestion/governance, or SQL execution.
