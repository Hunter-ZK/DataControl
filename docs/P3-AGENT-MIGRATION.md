# P3 DataAgent migration record

## Decision
DataControl is the final deliverable repository. `Hunter-ZK/DataAgent-dsh` is not a runtime service or second checkout; it is a pinned migration source.

Source: `Hunter-ZK/DataAgent-dsh`  
Commit: `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`

## Migrated into `agent/`
- harness-agnostic Agent3 Core and contracts;
- metadata, semantic compiler, SQL analysis/validation, policy, routing and evaluation port;
- MCP / HTTP / CLI protocol adapters;
- DataAgent Skills;
- pinned dsh package/profile/preset;
- guard plugin;
- semantic fixture and Agent-specific tests.

## DataControl-specific adaptation
Agent3 metadata uses a `PortalMetadataProvider` that reads DataControl facts through the Portal HTTP API. It does not import SQLAlchemy models or open the Portal database. Portal remains the authority for asset/metric facts.

The migration source historically pinned Python 3.14. DataControl no longer carries that pin forward: the embedded Agent package supports `>=3.13,<3.15`, CI verifies the Agent on Python 3.13 across Windows/macOS/Ubuntu, and local Portal/Agent processes share `.venv`. Process isolation is preserved by the Gateway/MCP contracts rather than by duplicate Python virtual environments.

## Gate status
Source migration and the supported dsh session bridge are implemented. `agent/runtime-manifest.json` remains `integrated=false` and `realModelAccepted=false` in Git because real-model acceptance is machine-local. A successful `scripts/p3_agent_acceptance.py` run with the user's model key writes `.local/p3-agent-acceptance.json`; SQL execution remains disabled throughout.
