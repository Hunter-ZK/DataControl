from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.app.core.config import SEARCH_DB


class SearchEngine:
    """Embedded derivative search index based on SQLite FTS5 trigram.

    Relational data remains the source of truth. This index is rebuilt from persisted
    asset facts and can be deleted/recreated at any time.
    """

    def __init__(self, path: Path = SEARCH_DB):
        self.path = path

    def connect(self):
        return sqlite3.connect(self.path)

    def rebuild(self, documents: list[dict]):
        self.path.parent.mkdir(exist_ok=True)
        with self.connect() as c:
            c.execute("DROP TABLE IF EXISTS asset_fts")
            c.execute(
                "CREATE VIRTUAL TABLE asset_fts USING fts5("
                "asset_id UNINDEXED, asset_type UNINDEXED, title, technical_name, body, "
                "tokenize='trigram')"
            )
            c.executemany(
                "INSERT INTO asset_fts VALUES (:asset_id,:asset_type,:title,:technical_name,:body)",
                documents,
            )

    @staticmethod
    def _literal_match(query: str) -> str:
        # Quote user input so FTS operators, punctuation and technical identifiers are
        # treated as data instead of executable MATCH syntax.
        return f'"{query.strip().replace(chr(34), chr(34) * 2)}"'

    def search(self, query: str, limit: int = 20, asset_types: list[str] | None = None):
        if not query.strip() or not self.path.exists():
            return []

        where = ["asset_fts MATCH ?"]
        params: list[object] = [self._literal_match(query)]
        if asset_types:
            placeholders = ",".join("?" for _ in asset_types)
            where.append(f"asset_type IN ({placeholders})")
            params.extend(asset_types)
        params.append(limit)

        sql = (
            "SELECT asset_id,asset_type,title,technical_name,"
            "highlight(asset_fts,2,'<mark>','</mark>') AS title_hl,"
            "highlight(asset_fts,3,'<mark>','</mark>') AS technical_name_hl,"
            "snippet(asset_fts,4,'<mark>','</mark>',' … ',18) AS snippet,"
            "bm25(asset_fts,0,0,8,7,2) AS score "
            f"FROM asset_fts WHERE {' AND '.join(where)} ORDER BY score LIMIT ?"
        )

        with self.connect() as c:
            c.row_factory = sqlite3.Row
            try:
                rows = c.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # FTS trigram needs sufficiently useful tokens. Short keywords and
                # unusual identifiers fall back to bounded LIKE matching.
                like = f"%{query.strip()}%"
                clauses = ["(title LIKE ? OR technical_name LIKE ? OR body LIKE ?)"]
                fallback_params: list[object] = [like, like, like]
                if asset_types:
                    placeholders = ",".join("?" for _ in asset_types)
                    clauses.append(f"asset_type IN ({placeholders})")
                    fallback_params.extend(asset_types)
                fallback_params.append(limit)
                rows = c.execute(
                    "SELECT asset_id,asset_type,title,technical_name,title AS title_hl,"
                    "technical_name AS technical_name_hl,substr(body,1,220) AS snippet,0 AS score "
                    f"FROM asset_fts WHERE {' AND '.join(clauses)} "
                    "ORDER BY CASE WHEN title LIKE ? THEN 0 WHEN technical_name LIKE ? THEN 1 ELSE 2 END, title "
                    "LIMIT ?",
                    fallback_params[:-1] + [like, like, fallback_params[-1]],
                ).fetchall()
            return [dict(r) for r in rows]

    def suggest(self, query: str, limit: int = 8):
        if not query.strip() or not self.path.exists():
            return []
        prefix = f"{query.strip()}%"
        contains = f"%{query.strip()}%"
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT asset_id,asset_type,title,technical_name FROM asset_fts "
                "WHERE title LIKE ? OR technical_name LIKE ? OR title LIKE ? OR technical_name LIKE ? "
                "ORDER BY CASE WHEN title LIKE ? THEN 0 WHEN technical_name LIKE ? THEN 1 ELSE 2 END, title "
                "LIMIT ?",
                (prefix, prefix, contains, contains, prefix, prefix, limit),
            ).fetchall()
            return [dict(r) for r in rows]
