from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Catalog(Base):
    __tablename__ = "ast_catalog"
    catalog_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_code: Mapped[str | None] = mapped_column(ForeignKey("ast_catalog.catalog_code"), nullable=True)
    catalog_name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(500))

class Dataset(Base):
    __tablename__ = "ast_dataset"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    biz_name: Mapped[str] = mapped_column(String(128), index=True)
    workspace_code: Mapped[str] = mapped_column(String(64), index=True)
    layer_code: Mapped[str] = mapped_column(String(8), index=True)
    catalog_code: Mapped[str] = mapped_column(ForeignKey("ast_catalog.catalog_code"), index=True)
    biz_definition: Mapped[str | None] = mapped_column(Text)
    stat_caliber: Mapped[str | None] = mapped_column(Text)
    data_source_desc: Mapped[str | None] = mapped_column(Text)
    grain: Mapped[str | None] = mapped_column(String(200))
    usage_notes: Mapped[str | None] = mapped_column(Text)
    tech_owner: Mapped[str | None] = mapped_column(String(64))
    biz_owner: Mapped[str | None] = mapped_column(String(64))
    owner_dept: Mapped[str | None] = mapped_column(String(128))
    update_freq: Mapped[str | None] = mapped_column(String(16))
    schedule_desc: Mapped[str | None] = mapped_column(String(300))
    schedule_node: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="ONLINE", index=True)
    is_common: Mapped[bool] = mapped_column(Boolean, default=False)
    storage_bytes: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    data_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    columns: Mapped[list["Column"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")

class Column(Base):
    __tablename__ = "ast_column"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    column_name: Mapped[str] = mapped_column(String(128), index=True)
    ordinal_no: Mapped[int] = mapped_column(Integer)
    cn_name: Mapped[str | None] = mapped_column(String(128), index=True)
    data_type: Mapped[str] = mapped_column(String(64))
    biz_definition: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32))
    code_table_no: Mapped[str | None] = mapped_column(String(64))
    standard_no: Mapped[str | None] = mapped_column(String(64))
    dataset: Mapped[Dataset] = relationship(back_populates="columns")
    __table_args__ = (UniqueConstraint("dataset_id", "column_name"),)

class TableLineage(Base):
    __tablename__ = "rel_table_lineage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_asset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    dst_asset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    task_name: Mapped[str | None] = mapped_column(String(128))
    evidence: Mapped[str] = mapped_column(String(16), default="CONFIRMED")

class Metric(Base):
    __tablename__ = "biz_metric"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    metric_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    aliases: Mapped[str | None] = mapped_column(String(500))
    biz_definition: Mapped[str | None] = mapped_column(Text)
    source_dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"))
    aggregation: Mapped[str] = mapped_column(String(16))
    measure_column: Mapped[str] = mapped_column(String(128))
    time_field: Mapped[str] = mapped_column(String(128), default="dt")
    caliber_desc: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="ONLINE")

class CodeTable(Base):
    __tablename__ = "std_code_table"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code_table_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_table_name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="EFFECTIVE")

class CodeValue(Base):
    __tablename__ = "std_code_value"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_table_no: Mapped[str] = mapped_column(ForeignKey("std_code_table.code_table_no"), index=True)
    code_value: Mapped[str] = mapped_column(String(64))
    code_name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
