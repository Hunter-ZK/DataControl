# 03 · Data model V3

## Identity
Every top-level asset has a stable `asset_id`. Physical/business identifiers remain unique but mutable.

Examples:
- dataset: `DS000001`
- field: `FD0000001`
- metric: `MT000001`
- code table: `CT000001`

Persistent application references must use asset IDs where identity stability matters.

## P0 implemented entities
`ast_catalog`, `ast_dataset`, `ast_column`, `rel_table_lineage`, `biz_metric`, `std_code_table`, `std_code_value`.

The final MySQL schema will be expanded during P1; P0 uses SQLAlchemy models so demo/CI can run on SQLite while production remains MySQL 8 compatible.
