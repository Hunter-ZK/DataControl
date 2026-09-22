from __future__ import annotations

import re

from agent3.contracts.authz import AuthzContext
from agent3.metadata.models import CodeValueMetadata, TableMetadata

_TOKEN = re.compile(r"[a-zA-Z0-9_\u4e00-\u9fff]+")


class InMemoryMetadataProvider:
    """Deterministic public provider used by tests and demos."""

    def __init__(
        self,
        tables: tuple[TableMetadata, ...],
        code_values: tuple[CodeValueMetadata, ...] = (),
    ) -> None:
        self._tables = {table.full_name.casefold(): table for table in tables}
        self._code_values = tuple(code_values)

    def all_tables(self, authz: AuthzContext) -> tuple[TableMetadata, ...]:
        _ = authz
        return tuple(self._tables.values())

    def get_table(self, authz: AuthzContext, full_name: str) -> TableMetadata | None:
        _ = authz
        key = full_name.casefold()
        if key in self._tables:
            return self._tables[key]
        if "." not in key:
            matches = [table for name, table in self._tables.items() if name.rsplit(".", 1)[-1] == key]
            return matches[0] if len(matches) == 1 else None
        return None

    def search_tables(
        self,
        authz: AuthzContext,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[TableMetadata, ...]:
        _ = authz
        tokens = {token.casefold() for token in _TOKEN.findall(query)}
        scored: list[tuple[int, str, TableMetadata]] = []
        for table in self._tables.values():
            haystack = " ".join([table.full_name, table.description, *table.aliases]).casefold()
            score = sum(
                3 if token in table.full_name.casefold() else 1
                for token in tokens
                if token in haystack
            )
            if score:
                scored.append((score, table.full_name, table))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in scored[: max(1, limit)])

    def resolve_code_values(
        self,
        authz: AuthzContext,
        code_table_no: str,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[CodeValueMetadata, ...]:
        _ = authz
        table_key = code_table_no.casefold()
        needle = query.strip().casefold()
        rows: list[tuple[int, CodeValueMetadata]] = []
        for item in self._code_values:
            if item.code_table_no.casefold() != table_key:
                continue
            if not needle:
                score = 1
            elif item.value.casefold() == needle or item.name.casefold() == needle:
                score = 100
            elif needle in item.name.casefold() or needle in item.description.casefold():
                score = 10
            else:
                continue
            rows.append((score, item))
        rows.sort(key=lambda value: (-value[0], value[1].value))
        return tuple(item for _, item in rows[: max(1, limit)])
