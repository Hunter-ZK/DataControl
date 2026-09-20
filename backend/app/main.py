from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.assets import router as assets_router
from backend.app.api.search import router as search_router
from backend.app.core.config import MODEL_NAME, MODEL_PROVIDER, ROOT

app = FastAPI(title="DataControl API", version="0.1.0-p0")
app.include_router(assets_router)
app.include_router(search_router)

@app.get("/health")
def health():
    return {"status": "ok", "phase": "P0"}

@app.get("/api/v1/system/info")
def system_info():
    return {"code": "OK", "data": {"phase": "P0", "modelProvider": MODEL_PROVIDER, "modelName": MODEL_NAME}}

prototype = ROOT / "web" / "prototype"
app.mount("/prototype", StaticFiles(directory=prototype), name="prototype")

@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(prototype / "index.html")
