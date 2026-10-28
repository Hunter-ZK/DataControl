"""Deterministic draft-only warehouse development helpers.

These functions generate proposed statements; none has a database execution path.
They require concrete source columns or user-supplied schema and reject raw SQL fragments.
"""
from __future__ import annotations

import re
from typing import Any

_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_QUALIFIED = re.compile(r"^[a-z][a-z0-9_]{0,127}(?:\.[a-z][a-z0-9_]{0,127})?$")
_TYPE = re.compile(r"^(?:STRING|BIGINT|INT|DOUBLE|BOOLEAN|DATE|DATETIME|TIMESTAMP|FLOAT|DECIMAL\([1-9][0-9]?,[0-9]{1,2}\))$", re.I)


def identifier(name: str, *, qualified: bool = False) -> str:
    pattern = _QUALIFIED if qualified else _IDENT
    if not isinstance(name, str) or not pattern.fullmatch(name):
        raise ValueError("Invalid warehouse identifier; expected lowercase snake_case")
    return name


def check_naming(name: str, *, roots: set[str] | None = None) -> dict[str, Any]:
    compliant = bool(_IDENT.fullmatch(name))
    parts = name.split("_")
    unknown = sorted(set(parts) - roots) if roots else []
    return {
        "name": name, "validFormat": compliant, "parts": parts,
        "unknownRoots": unknown, "rootCoverageChecked": roots is not None,
        "status": "valid" if compliant and not unknown else "review_required",
        "execution_allowed": False,
    }


def generate_ddl(table: str, columns: list[dict[str, Any]], *,
                 comment: str = "", partition_key: str | None = None) -> dict[str, Any]:
    table = identifier(table, qualified=True)
    if not columns or len(columns) > 200:
        raise ValueError("1..200 explicitly specified columns are required")
    defs = []
    seen = set()
    for row in columns:
        if not isinstance(row, dict):
            raise ValueError("Each column requires name and type")
        name = identifier(row.get("name", ""))
        col_type = str(row.get("type", "")).upper()
        if not _TYPE.fullmatch(col_type):
            raise ValueError(f"Unsupported or unsafe type for {name}")
        if name in seen:
            raise ValueError(f"Duplicate column: {name}")
        seen.add(name)
        label = str(row.get("comment") or "").replace("'", "''")[:240]
        defs.append(f"  {name} {col_type}" + (f" COMMENT '{label}'" if label else ""))
    if partition_key:
        partition_key = identifier(partition_key)
        if partition_key in seen:
            raise ValueError("Partition key must not appear twice")
    text = f"CREATE TABLE IF NOT EXISTS {table} (\n" + ",\n".join(defs) + "\n)"
    if comment:
        text += " COMMENT '" + comment.replace("'", "''")[:240] + "'"
    if partition_key:
        text += f" PARTITIONED BY ({partition_key} STRING)"
    return {
        "sql": text + ";", "status": "draft_requires_human_review",
        "execution_allowed": False, "requiresApproval": True,
        "warnings": ["DDL is a proposal only; no production SQL/DDL is executed."],
    }


def generate_etl(source_table: str, target_table: str,
                 mappings: list[dict[str, str]], available_columns: set[str],
                 *, source_partition: str | None = None) -> dict[str, Any]:
    source_table = identifier(source_table, qualified=True)
    target_table = identifier(target_table, qualified=True)
    if not mappings or len(mappings) > 200:
        raise ValueError("Explicit 1..200 field mappings are required")
    sources = []
    targets = []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise ValueError("Mappings must be objects")
        src = identifier(mapping.get("source", ""))
        dst = identifier(mapping.get("target", ""))
        if src not in available_columns:
            raise ValueError(f"Source column is not governed: {src}")
        sources.append(src)
        targets.append(dst)
    if len(set(targets)) != len(targets):
        raise ValueError("Duplicate target columns")
    projection = ",\n  ".join(
        f"src.{source} AS {target}" for source, target in zip(sources, targets)
    )
    statement = f"INSERT OVERWRITE TABLE {target_table}\nSELECT\n  {projection}\nFROM {source_table} src"
    if source_partition:
        part = identifier(source_partition)
        if part not in available_columns:
            raise ValueError("Partition field not present in governed source")
        statement += f"\nWHERE src.{part} = '${{dt}}'"
    return {
        "sql": statement + ";", "status": "draft_requires_human_review",
        "execution_allowed": False, "requiresApproval": True,
        "sourceTable": source_table, "targetTable": target_table,
        "warnings": ["Target grain, partition strategy and deployment require human confirmation.",
                     "This is a single-source direct mapping draft without inferred joins."],
    }


def generate_dq_checks(table: str, available_columns: set[str], *,
                       required_columns: list[str] | None = None,
                       unique_keys: list[str] | None = None) -> dict[str, Any]:
    table = identifier(table, qualified=True)
    required = required_columns or []
    keys = unique_keys or []
    for name in [*required, *keys]:
        if identifier(name) not in available_columns:
            raise ValueError(f"Unknown governed column: {name}")
    if len(required) > 40 or len(keys) > 10:
        raise ValueError("Too many quality rules")
    checks = [{
        "rule": "row_count", "sql": f"SELECT COUNT(*) AS row_count FROM {table};",
        "expected": "Review against an agreed source reconciliation count",
    }]
    for col in dict.fromkeys(required):
        checks.append({
            "rule": f"not_null:{col}",
            "sql": f"SELECT COUNT(*) AS null_count FROM {table} WHERE {col} IS NULL;",
            "expected": "null_count = 0 if the field is governed as required",
        })
    if keys:
        key_names = ", ".join(dict.fromkeys(keys))
        checks.append({
            "rule": "unique_key",
            "sql": (f"SELECT {key_names}, COUNT(*) AS duplicate_count FROM {table} "
                    f"GROUP BY {key_names} HAVING COUNT(*) > 1;"),
            "expected": "No duplicate key rows if the target grain is confirmed",
        })
    return {"checks": checks, "execution_allowed": False, "status": "draft_only",
            "warnings": ["No check has been executed; thresholds must be confirmed by data owners."]}
