from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_upgrade_from_pre_alembic_p0_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_p0.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        );
        INSERT INTO alembic_version(version_num) VALUES ('20260920_0001');

        CREATE TABLE std_code_table (
            asset_id VARCHAR(32) NOT NULL PRIMARY KEY,
            code_table_no VARCHAR(64) NOT NULL UNIQUE,
            code_table_name VARCHAR(128) NOT NULL,
            description TEXT,
            status VARCHAR(16) NOT NULL
        );
        INSERT INTO std_code_table(asset_id, code_table_no, code_table_name, description, status)
        VALUES ('CT000001', 'CD_STATUS', '业务状态', 'legacy row', 'EFFECTIVE');

        CREATE TABLE biz_metric (
            asset_id VARCHAR(32) NOT NULL PRIMARY KEY,
            metric_code VARCHAR(64) NOT NULL UNIQUE,
            metric_name VARCHAR(128) NOT NULL,
            aliases VARCHAR(500),
            biz_definition TEXT,
            source_dataset_id VARCHAR(32) NOT NULL,
            aggregation VARCHAR(16) NOT NULL,
            measure_column VARCHAR(128) NOT NULL,
            time_field VARCHAR(128) NOT NULL,
            caliber_desc TEXT,
            status VARCHAR(16) NOT NULL
        );
        INSERT INTO biz_metric(
            asset_id, metric_code, metric_name, source_dataset_id,
            aggregation, measure_column, time_field, status
        ) VALUES (
            'MT000001', 'metric_001', '各项贷款余额', 'DS000001',
            'sum', 'balance_amt', 'dt', 'ONLINE'
        );
        """
    )
    connection.commit()
    connection.close()

    env = os.environ.copy()
    env["DATACONTROL_DATABASE_URL"] = f"sqlite:///{db_path}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    connection = sqlite3.connect(db_path)
    try:
        code_columns = _columns(connection, "std_code_table")
        metric_columns = _columns(connection, "biz_metric")
        assert {"en_name", "category_code", "source_standard", "version", "owner"} <= code_columns
        assert {"stat_system_code", "time_additivity", "valid_dimensions"} <= metric_columns

        code_row = connection.execute(
            "SELECT code_table_name, description FROM std_code_table WHERE asset_id='CT000001'"
        ).fetchone()
        metric_row = connection.execute(
            "SELECT metric_name, time_additivity FROM biz_metric WHERE asset_id='MT000001'"
        ).fetchone()
        assert code_row == ("业务状态", "legacy row")
        assert metric_row == ("各项贷款余额", "ADDITIVE")

        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert revision == "20260920_0002"
    finally:
        connection.close()
