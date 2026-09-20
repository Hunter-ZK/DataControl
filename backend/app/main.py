from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.activity import router as activity_router
from backend.app.api.assets import router as assets_router
from backend.app.api.auth import router as auth_router
from backend.app.api.details import router as details_router
from backend.app.api.reference import router as reference_router
from backend.app.api.search import router as search_router
from backend.app.core.config import MODEL_NAME, MODEL_PROVIDER, ROOT
from backend.app.db.application_models import AuditLog, SearchHistory  # noqa: F401

app = FastAPI(title="DataControl API", version="0.3.0-p2")
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(details_router)
app.include_router(reference_router)
app.include_router(search_router)
app.include_router(activity_router)


@app.get("/health")
def health():
    return {"status": "ok", "phase": "P2"}


@app.get("/api/v1/system/info")
def system_info():
    return {
        "code": "OK",
        "data": {
            "phase": "P2",
            "modelProvider": MODEL_PROVIDER,
            "modelName": MODEL_NAME,
            "platforms": ["windows", "macos"],
        },
    }


prototype = ROOT / "web" / "prototype"
if prototype.exists():
    app.mount("/prototype", StaticFiles(directory=prototype), name="prototype")

dist = ROOT / "web" / "dist"
if (dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="web-assets")


def _spa_response(path: str = ""):
    if (dist / "index.html").exists():
        return FileResponse(dist / "index.html")
    suffix = f"/{path}" if path else "/"
    return RedirectResponse(f"http://127.0.0.1:5173{suffix}", status_code=307)


@app.get("/", include_in_schema=False)
def ui():
    return _spa_response()


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """Serve Vue history-mode routes without masking unknown API paths."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return _spa_response(full_path)
