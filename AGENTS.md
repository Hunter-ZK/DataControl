# AI coding rules

1. Product documents under `docs/` are the source of truth.
2. The portal is read-only for asset facts. Do not add ingestion/governance/editing without an approved phase change.
3. Do not execute user SQL. Agent capability stops at generation, deterministic validation and explanation.
4. Stable identity uses `asset_id`; physical names are mutable attributes.
5. Keep boundaries: API -> service -> repository -> persistence/search. Do not put SQL in route handlers.
6. Portal backend and Agent3 may both use Python but remain separate modules. Agent3 reads asset facts through portal internal APIs.
7. Do not expose model chain-of-thought. UI may show tool/activity summaries only.
8. No secrets or real asset data in the repository.
