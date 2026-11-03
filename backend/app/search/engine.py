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
        needle = query.strip()
        if not needle or not self.path.exists():
            return empty
        # SQLite FTS5 trigram MATCH cannot find shorter than three characters.
        # Use a bounded-result LIKE fallback for one/two-character queries.
        if len(needle) < 3:
            where = "(title LIKE ? OR technical_name LIKE ? OR body LIKE ?)"
            value = f"%{needle}%"
            params = [value, value, value]
            excerpt_expr = "substr(body, 1, 120)"
            rank_expr = "0.0"
        else:
            where = "asset_fts MATCH ?"
            params = [needle]
            excerpt_expr = "snippet(asset_fts, 4, '', '', '…', 18)"
            rank_expr = "bm25(asset_fts, 0, 0, 5, 4, 2)"
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            counts = c.execute(
                "SELECT asset_type, COUNT(*) AS n FROM asset_fts WHERE " +
                where + " GROUP BY asset_type", tuple(params)
            ).fetchall()
            facets = {row["asset_type"]: row["n"] for row in counts}
            total = sum(facets.values()) if asset_type == "ALL" else facets.get(asset_type, 0)
            clause = "" if asset_type == "ALL" else " AND asset_type = ?"
            args = params.copy()
            if asset_type != "ALL":
                args.append(asset_type)
            rows = c.execute(
                "SELECT asset_id, asset_type, title, technical_name, " +
                excerpt_expr + " AS excerpt, " + rank_expr + " AS score "
                "FROM asset_fts WHERE " + where + clause +
                " ORDER BY score, asset_id LIMIT ? OFFSET ?",
                (*args, limit, offset),
            ).fetchall()
            return {"items": [dict(row) for row in rows], "total": total, "facets": facets}
