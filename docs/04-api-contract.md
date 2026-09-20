# 04 · API contract V3 P0

Envelope: `{ "code": "OK", "data": ... }`.

Implemented P0 endpoints:
- `GET /health`
- `GET /api/v1/system/info`
- `GET /api/v1/tables?limit=&keyword=`
- `GET /api/v1/tables/{asset_id}`
- `GET /api/v1/search?q=&limit=`

P1 expands the complete REST and internal API contract. Public asset detail URLs may remain human-readable, but persistent references use stable IDs.
