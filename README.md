# DataControl / DataPortal

P0 foundation for a read-only data asset service portal.

## P0 scope
- Python/FastAPI backend foundation
- stable `asset_id` identity model
- rich synthetic demo dataset
- embedded SQLite FTS5 search spike
- ACP/dsh integration boundary and smoke-test harness
- visual design-system prototype with a refreshed light ocean-blue palette
- search-first home portal with immediate result preview and module launchers
- standalone Data Overview page
- dataset detail reference page with scheduling folded into the asset view
- Windows + macOS local development support
- no DataWorks/MaxCompute ingestion, no governance workflow, no SQL execution

## Windows quick start

```powershell
.\scripts\setup-dev.ps1
.\scripts\verify.ps1
.\scripts\start-dev.ps1
```

## macOS quick start

```bash
bash scripts/setup-dev.sh
bash scripts/verify.sh
bash scripts/start-dev.sh
```

Optional:

```bash
chmod +x scripts/*.sh
```

Then run the shell scripts directly with `./scripts/...`.

Open:
- UI prototype: http://127.0.0.1:8000/
- OpenAPI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

For the intended production database, set `DATACONTROL_DATABASE_URL` to a MySQL 8 SQLAlchemy URL. Demo/CI defaults to SQLite so P0 can be verified without infrastructure.

## Portability guarantee
- CI runs on Windows, macOS and Ubuntu.
- Runtime Python code must remain platform-neutral.
- PowerShell and shell scripts provide equivalent setup/start/verify workflows.
