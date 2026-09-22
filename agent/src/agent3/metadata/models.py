from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodeValueMetadata:
    code_table_no: str
    value: str
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class ColumnMetadata:
    name: str
    data_type: str
    description: str = ""
    nullable: bool = True
    sensitive: bool = False
    code_table_no: str = ""
    standard_no: str = ""


@dataclass(frozen=True, slots=True)
class TableMetadata:
    full_name: str
    description: str = ""
    columns: tuple[ColumnMetadata, ...] = ()
    partition_fields: tuple[str, ...] = ()
    row_count_estimate: int | None = None
    aliases: tuple[str, ...] = ()

    def column(self, name: str) -> ColumnMetadata | None:
        folded = name.casefold()
        return next((column for column in self.columns if column.name.casefold() == folded), None)

    @property
    def column_names(self) -> frozenset[str]:
        return frozenset(column.name.casefold() for column in self.columns)
