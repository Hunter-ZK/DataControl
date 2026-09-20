from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.session import SessionLocal
from backend.app.search.indexer import rebuild_search_index


def main() -> None:
    with SessionLocal() as db:
        count = rebuild_search_index(db)
    print(f"Unified search index rebuilt: {count} assets")


if __name__ == "__main__":
    main()
