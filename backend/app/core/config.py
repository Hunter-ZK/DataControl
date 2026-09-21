from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / ".local"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATACONTROL_DATABASE_URL", f"sqlite:///{DATA_DIR / 'datacontrol.db'}")
SEARCH_DB = Path(os.getenv("DATACONTROL_SEARCH_DB", str(DATA_DIR / "search.db")))
MODEL_PROVIDER = os.getenv("DATACONTROL_MODEL_PROVIDER", "deepseek")
MODEL_NAME = os.getenv("DATACONTROL_MODEL_NAME", "deepseek-chat")

# P3 monorepo boundary. The DataAgent implementation is owned by this repository
# under DataControl/agent. DataAgent-dsh is a migration source/baseline only; a
# deployed DataControl instance must never depend on cloning or importing another
# Git repository at runtime.
AGENT_HOME = Path(os.getenv("DATACONTROL_AGENT_HOME", str(ROOT / "agent"))).resolve()
AGENT_GATEWAY_URL = os.getenv("DATACONTROL_AGENT_GATEWAY_URL", "http://127.0.0.1:8910").rstrip("/")
AGENT_TIMEOUT_SECONDS = float(os.getenv("DATACONTROL_AGENT_TIMEOUT_SECONDS", "120"))
