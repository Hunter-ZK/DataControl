# 08 · Security boundary

## Portal

- user-facing asset services remain read-only;
- authentication/authorization is enforced by Portal endpoints;
- stable asset IDs are used for references;
- application audit data remains Portal-owned.

## Embedded DataAgent

- DataAgent code is shipped under `DataControl/agent`, not fetched from another repository at runtime;
- dsh is a replaceable Agent Runtime, not a security boundary by itself;
- MCP/HTTP/CLI adapters must remain thin protocol projections;
- Agent3 Core owns deterministic semantic/SQL validation and policy decisions;
- production database credentials are never given to dsh;
- production SQL execution is disabled in the current product boundary;
- unexpected write/approval surfaces are rejected unless explicitly introduced by a later approved scope;
- hidden model reasoning is not exposed to the Portal.

## Migration gate

The source baseline is `Hunter-ZK/DataAgent-dsh@f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`. Migration must preserve its architecture/security invariants rather than blindly copy files. `agent/runtime-manifest.json` remains `integrated: false` until the local runtime and end-to-end acceptance pass.
