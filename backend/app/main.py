from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.activity import router as activity_router
from backend.app.api.assets import router as assets_router
from backend.app.api.auth import router as auth_router
from backend.app.api.details import router as details_router
from backend.app.api.reference import router as reference_router
from backend.app.api.search import router as search_router
from backend.app.core.config import MODEL_NAME, MODEL_PROVIDER, ROOT
from backend.app.db.application_models import AuditLog, SearchHistory  # noqa: F401

app = FastAPI(title="DataControl API", version="0.2.0-p1")
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(details_router)
app.include_router(reference_router)
app.include_router(search_router)
app.include_router(activity_router)


@app.get("/health")
def health():
    return {"status": "ok", "phase": "P1"}


@app.get("/api/v1/system/info")
def system_info():
    return {
        "code": "OK",
        "data": {
            "phase": "P1",
            "modelProvider": MODEL_PROVIDER,
            "modelName": MODEL_NAME,
            "platforms": ["windows", "macos"],
        },
    }


prototype = ROOT / "web" / "prototype"
app.mount("/prototype", StaticFiles(directory=prototype), name="prototype")


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(
        prototype / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
