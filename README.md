# DataControl / DataPortal

P0 foundation for a read-only data asset service portal.

## P0 scope
- Python/FastAPI backend foundation
- stable `asset_id` identity model
- rich synthetic validation data at both quick-demo and full target scale
- embedded SQLite FTS5 search spike
- dsh + Agent3 integration boundary
- visual design-system prototype: dashboard + dataset detail
- no DataWorks/MaxCompute ingestion, no governance workflow, no SQL execution

## Quick start (demo mode, no MySQL required)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python samples/generate_demo_data.py
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open:
- UI prototype: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Full-scale test data

For performance, search and UI-density verification at the scale of the current asset inventory:

```powershell
python samples/generate_full_scale.py
```

This generates **1,361 datasets, 54,440 fields, 126 metrics, 40 code tables and 55,000+ search documents**, plus lineage, statuses, owners, schedules, volumes and mixed business domains.

For the intended production database, set `DATACONTROL_DATABASE_URL` to a MySQL 8 SQLAlchemy URL. Demo/CI defaults to SQLite so P0 can be verified without infrastructure.

## Verify

```powershell
python scripts/verify.py
```
