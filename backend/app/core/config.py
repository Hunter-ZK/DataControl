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

# P3 external-agent boundary. The portal owns UI/session delivery only; dsh owns
# the model loop and Agent3 remains a separate capability service exposed through MCP.
DSH_COMMAND = os.getenv("DATACONTROL_DSH_COMMAND", "npx @deepseek-ai/dsh --profile acp")
AGENT3_MCP_URL = os.getenv("DATACONTROL_AGENT3_MCP_URL", "")
AGENT_WORKSPACE = Path(os.getenv("DATACONTROL_AGENT_WORKSPACE", str(ROOT))).resolve()
AGENT_TIMEOUT_SECONDS = float(os.getenv("DATACONTROL_AGENT_TIMEOUT_SECONDS", "120"))
