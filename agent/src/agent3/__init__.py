"""Agent3 Data Intelligence Core embedded in DataControl.

Core remains independent of DeepSeek Harness, MCP, HTTP and UI frameworks.
Adapters depend on Core; Core never depends on adapters.
"""
from agent3.services.core import Agent3Core

__all__ = ["Agent3Core"]
__version__ = "0.3.0"
