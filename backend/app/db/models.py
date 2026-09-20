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


class Tag(Base):
    __tablename__ = "ast_tag"
    tag_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    tag_name: Mapped[str] = mapped_column(String(64), index=True)
    tag_group: Mapped[str] = mapped_column(String(32), default="CUSTOM")


class DatasetTag(Base):
    __tablename__ = "ast_dataset_tag"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), primary_key=True)
    tag_code: Mapped[str] = mapped_column(ForeignKey("ast_tag.tag_code"), primary_key=True)


class ChangeLog(Base):
    __tablename__ = "ast_change_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    change_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    change_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str | None] = mapped_column(String(64))


class CommonSql(Base):
    __tablename__ = "ast_common_sql"
    sql_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    question: Mapped[str | None] = mapped_column(String(1000))
    sql_text: Mapped[str] = mapped_column(Text)
    dialect: Mapped[str] = mapped_column(String(32), default="maxcompute")
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="VALID")


class CommonSqlDataset(Base):
    __tablename__ = "ast_common_sql_dataset"
    sql_code: Mapped[str] = mapped_column(ForeignKey("ast_common_sql.sql_code"), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), primary_key=True)


class TableLineage(Base):
    __tablename__ = "rel_table_lineage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_asset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    dst_asset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    task_name: Mapped[str | None] = mapped_column(String(128))
    evidence: Mapped[str] = mapped_column(String(16), default="CONFIRMED")


class StatisticalSystem(Base):
    __tablename__ = "biz_stat_system"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    stat_system_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    stat_system_name: Mapped[str] = mapped_column(String(200), index=True)
    version: Mapped[str | None] = mapped_column(String(32))
    issuer: Mapped[str | None] = mapped_column(String(128))
    document_no: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="EFFECTIVE")


class Metric(Base):
    __tablename__ = "biz_metric"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    metric_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True)
    aliases: Mapped[str | None] = mapped_column(String(500))
    biz_definition: Mapped[str | None] = mapped_column(Text)
    source_dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"))
    stat_system_code: Mapped[str | None] = mapped_column(String(64))
    aggregation: Mapped[str] = mapped_column(String(16))
    measure_column: Mapped[str] = mapped_column(String(128))
    time_field: Mapped[str] = mapped_column(String(128), default="dt")
    time_additivity: Mapped[str] = mapped_column(String(16), default="ADDITIVE")
    caliber_desc: Mapped[str | None] = mapped_column(Text)
    valid_dimensions: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), default="ONLINE")


class StandardCategory(Base):
    __tablename__ = "std_category"
    category_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_type: Mapped[str] = mapped_column(String(24), index=True)
    parent_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category_name: Mapped[str] = mapped_column(String(64))


class CodeTable(Base):
    __tablename__ = "std_code_table"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code_table_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    code_table_name: Mapped[str] = mapped_column(String(128), index=True)
    en_name: Mapped[str | None] = mapped_column(String(128))
    category_code: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    source_standard: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[str | None] = mapped_column(String(32))
    owner: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="EFFECTIVE")


class CodeValue(Base):
    __tablename__ = "std_code_value"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_table_no: Mapped[str] = mapped_column(ForeignKey("std_code_table.code_table_no"), index=True)
    code_value: Mapped[str] = mapped_column(String(64))
    code_name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(String(500))


class DataStandard(Base):
    __tablename__ = "std_data_standard"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    standard_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    standard_name: Mapped[str] = mapped_column(String(128), index=True)
    en_name: Mapped[str | None] = mapped_column(String(128))
    category_code: Mapped[str | None] = mapped_column(String(64))
    business_definition: Mapped[str | None] = mapped_column(Text)
    business_rule: Mapped[str | None] = mapped_column(Text)
    data_type: Mapped[str | None] = mapped_column(String(64))
    code_table_no: Mapped[str | None] = mapped_column(String(64))
    owner_dept: Mapped[str | None] = mapped_column(String(128))
    version: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="EFFECTIVE")


class WordRoot(Base):
    __tablename__ = "std_word_root"
    asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    root_en: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    cn_name: Mapped[str] = mapped_column(String(64), index=True)
    en_full: Mapped[str | None] = mapped_column(String(128))
    synonyms: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), default="EFFECTIVE")


class User(Base):
    __tablename__ = "sys_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16), default="USER")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")


class Favorite(Base):
    __tablename__ = "sys_favorite"
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(24), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ViewLog(Base):
    __tablename__ = "sys_view_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(24))
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
