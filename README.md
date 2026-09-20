# DataControl / DataPortal

P0 foundation for a read-only data asset service portal.

## P0 scope
- Python/FastAPI backend foundation
- stable `asset_id` identity model
- rich synthetic demo dataset
- embedded SQLite FTS5 search spike
- ACP/dsh integration boundary and smoke-test harness
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

For the intended production database, set `DATACONTROL_DATABASE_URL` to a MySQL 8 SQLAlchemy URL. Demo/CI defaults to SQLite so P0 can be verified without infrastructure.

## Verify

```powershell
python scripts/verify.py
```
