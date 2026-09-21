from __future__ import annotations

import os
from pathlib import Path

from agent3.metadata.datacontrol_http import PortalMetadataProvider
from agent3.metadata.demo import build_demo_metadata
from agent3.semantic.datacontrol import load_portal_semantics
from agent3.semantic.registry import SemanticRegistry
from agent3.services.core import Agent3Core


def build_demo_core() -> Agent3Core:
    root = Path(__file__).resolve().parents[3]
    semantics = SemanticRegistry.from_yaml(root / "semantic_models" / "loan.yaml")
    return Agent3Core(metadata=build_demo_metadata(), semantics=semantics)


def build_datacontrol_core() -> Agent3Core:
    base_url = os.getenv("DATACONTROL_PORTAL_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    metadata = PortalMetadataProvider(base_url)
    semantics = load_portal_semantics(base_url, metadata)
    return Agent3Core(metadata=metadata, semantics=semantics)
