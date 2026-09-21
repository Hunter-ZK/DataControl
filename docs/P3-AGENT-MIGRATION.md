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
Agent3 metadata now has a `PortalMetadataProvider` that reads DataControl facts through the Portal HTTP API. It does not import SQLAlchemy models or open the Portal database. Portal remains the authority for asset/metric facts.

Portal stays on Python 3.13 while DataAgent keeps Python 3.14. The repository therefore uses `.venv` and `.venv-agent`, with separate CI jobs on Windows, macOS and Ubuntu.

## Gate status
`agent/runtime-manifest.json` has `sourceMigrated=true` but `integrated=false`. This is intentional. The next gate is to establish a supported DataControl-to-dsh session bridge and verify one real model request through dsh -> MCP -> Agent3 Core without SQL execution. Until then the product UI reports the Agent as not ready rather than fabricating success.
