from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from backend.app.core.config import SEARCH_DB


class SearchEngine:
    """Embedded derivative search index with token-aware literal matching.

    The FTS5 table remains a disposable derivative index, while P1 deliberately
    uses literal predicates over its content columns for result correctness:
    two-character Chinese terms, whitespace-separated queries and technical
    identifiers no longer inherit trigram MATCH token limits. At the intended
    thousands/tens-of-thousands scale this bounded embedded scan keeps exact
    result/facet accounting without introducing another search service.
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
    def _terms(query: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(x for x in re.split(r"\s+", query.strip()) if x))

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")

    @classmethod
    def _highlight(cls, value: str, terms: tuple[str, ...]) -> str:
        if not value or not terms:
            return value
        pattern = re.compile(
            "(" + "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True)) + ")",
            flags=re.IGNORECASE,
        )
        return pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", value)

    @staticmethod
    def _relevance(row: sqlite3.Row, query: str, terms: tuple[str, ...]) -> float:
        title = str(row["title"] or "").casefold()
        technical = str(row["technical_name"] or "").casefold()
        body = str(row["body"] or "").casefold()
        phrase = " ".join(query.strip().split()).casefold()
        folded_terms = tuple(term.casefold() for term in terms)

        if title == phrase:
            return 0.0
        if technical == phrase:
            return 0.1
        if title.startswith(phrase):
            return 0.4
        if technical.startswith(phrase):
            return 0.6
        if phrase and phrase in title:
            return 0.9
        if phrase and phrase in technical:
            return 1.1

        title_hits = sum(term in title for term in folded_terms)
        tech_hits = sum(term in technical for term in folded_terms)
        body_hits = sum(term in body for term in folded_terms)
        # Lower is better, preserving the old bm25-facing ordering convention.
        return round(10.0 - title_hits * 2.0 - tech_hits * 1.5 - body_hits * 0.25, 4)

    def search(
        self,
        query: str,
        limit: int | None = 20,
        asset_types: list[str] | None = None,
    ) -> list[dict]:
        terms = self._terms(query)
        if not terms or not self.path.exists():
            return []

        where: list[str] = []
        params: list[object] = []
        for term in terms:
            pattern = f"%{self._escape_like(term)}%"
            where.append(
                "(title LIKE ? ESCAPE '!' OR technical_name LIKE ? ESCAPE '!' "
                "OR body LIKE ? ESCAPE '!')"
            )
            params.extend([pattern, pattern, pattern])
        if asset_types:
            placeholders = ",".join("?" for _ in asset_types)
            where.append(f"asset_type IN ({placeholders})")
            params.extend(asset_types)

        sql = (
            "SELECT asset_id,asset_type,title,technical_name,body "
            f"FROM asset_fts WHERE {' AND '.join(where)}"
        )
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(sql, params).fetchall()

        ranked: list[dict] = []
        for row in rows:
            data = dict(row)
            data["score"] = self._relevance(row, query, terms)
            data["title_hl"] = self._highlight(str(row["title"] or ""), terms)
            data["technical_name_hl"] = self._highlight(str(row["technical_name"] or ""), terms)
            body = str(row["body"] or "")
            data["snippet"] = self._highlight(body[:260], terms)
            data.pop("body", None)
            ranked.append(data)

        ranked.sort(key=lambda item: (float(item["score"]), str(item["title"]), str(item["asset_id"])))
        return ranked if limit is None else ranked[: max(0, limit)]

    def suggest(self, query: str, limit: int = 8):
        if not query.strip() or not self.path.exists():
            return []
        escaped = self._escape_like(query.strip())
        prefix = f"{escaped}%"
        contains = f"%{escaped}%"
        with self.connect() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT asset_id,asset_type,title,technical_name FROM asset_fts "
                "WHERE title LIKE ? ESCAPE '!' OR technical_name LIKE ? ESCAPE '!' "
                "OR title LIKE ? ESCAPE '!' OR technical_name LIKE ? ESCAPE '!' "
                "ORDER BY CASE WHEN title LIKE ? ESCAPE '!' THEN 0 "
                "WHEN technical_name LIKE ? ESCAPE '!' THEN 1 ELSE 2 END, title LIMIT ?",
                (prefix, prefix, contains, contains, prefix, prefix, limit),
            ).fetchall()
            return [dict(row) for row in rows]
