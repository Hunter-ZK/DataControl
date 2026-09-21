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

## P3 DataAgent monorepo acceptance

The Agent readiness gate is closed until every item below passes:

1. `DataControl/agent` contains the runtime assets migrated from the pinned `DataAgent-dsh` baseline.
2. Runtime startup does not clone or import another Git repository.
3. Portal calls only the local Agent Gateway contract; it does not import Agent3 Core.
4. DataAgent keeps `dsh/UI/API -> adapters -> Agent3 Core -> domain/ports` dependency direction.
5. MCP stays an adapter and contains no duplicated business rules.
6. Windows and macOS setup/start/verify scripts can install and launch the embedded Agent runtime from the DataControl checkout.
7. Python compatibility is explicitly resolved: the DataAgent source baseline declares Python 3.14 and this requirement may not be silently downgraded.
8. DataAgent architecture/security tests pass after migration.
9. dsh can call the embedded MCP tools.
10. Portal can reach the local Agent Gateway and complete at least one real model-backed Q&A flow.
11. SQL execution remains disabled and is asserted in the returned contract.
12. Hidden model reasoning is not exposed.
13. `agent/runtime-manifest.json` is changed to `integrated: true` only after items 1–12 pass.

Until then, `/api/v1/agent/status` must report not-ready instead of returning a simulated success.

## P4 production acceptance

SSO/LDAP, production DB deployment, fine-grained security, audit/observability, caching and operational deployment are P4 concerns and are not prerequisites for P3 functional acceptance unless they become necessary to close a security boundary.
