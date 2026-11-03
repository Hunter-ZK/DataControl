from __future__ import annotations
import sqlite3
from pathlib import Path
from backend.app.core.config import SEARCH_DB

class SearchEngine:
    """Embedded P0 search engine using SQLite FTS5 trigram."""

    def __init__(self, path: Path = SEARCH_DB):
        self.path = path

    def connect(self):
        return sqlite3.connect(self.path)

    def rebuild(self, documents: list[dict]):
        self.path.parent.mkdir(exist_ok=True)
        with self.connect() as c:
            c.execute("DROP TABLE IF EXISTS asset_fts")
            c.execute("CREATE VIRTUAL TABLE asset_fts USING fts5(asset_id UNINDEXED, asset_type UNINDEXED, title, technical_name, body, tokenize='trigram')")
            c.executemany("INSERT INTO asset_fts VALUES (:asset_id,:asset_type,:title,:technical_name,:body)", documents)

    def search(self, query: str, limit: int = 20):
        if not query.strip() or not self.path.exists():
            return []
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT asset_id,asset_type,title,technical_name,highlight(asset_fts,2,'<mark>','</mark>') AS title_hl,bm25(asset_fts,0,0,5,4,2) AS score FROM asset_fts WHERE asset_fts MATCH ? ORDER BY score LIMIT ?",
                (query.strip(), limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_page(
        self, query: str, *, limit: int = 20, offset: int = 0,
        asset_type: str = "ALL",
    ) -> dict:
        empty = {"items": [], "total": 0, "facets": {}}
        if not query.strip() or not self.path.exists():
            return empty
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            counts = c.execute(
                "SELECT asset_type, COUNT(*) AS n FROM asset_fts "
                "WHERE asset_fts MATCH ? GROUP BY asset_type", (query.strip(),)
            ).fetchall()
            facets = {row["asset_type"]: row["n"] for row in counts}
            total = sum(facets.values()) if asset_type == "ALL" else facets.get(asset_type, 0)
            clause = "" if asset_type == "ALL" else " AND asset_type = ?"
            params = [query.strip()]
            if asset_type != "ALL":
                params.append(asset_type)
            rows = c.execute(
                "SELECT asset_id, asset_type, title, technical_name, "
                "snippet(asset_fts, 4, '', '', '…', 18) AS excerpt, "
                "bm25(asset_fts, 0, 0, 5, 4, 2) AS score "
                "FROM asset_fts WHERE asset_fts MATCH ?" + clause +
                " ORDER BY score LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
            return {"items": [dict(row) for row in rows], "total": total, "facets": facets}
