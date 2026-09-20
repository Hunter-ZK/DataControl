from pathlib import Path
from backend.app.search.engine import SearchEngine


def test_search_chinese_and_technical(tmp_path: Path):
    engine = SearchEngine(tmp_path / "search.db")
    engine.rebuild([
        {
            "asset_id": "DS000001",
            "asset_type": "TABLE",
            "title": "贷款余额日快照",
            "technical_name": "stat_prod.dwd_loan_snapshot",
            "body": "各项贷款余额 监管统计",
        }
    ])
    assert engine.search("贷款余额")[0]["asset_id"] == "DS000001"
    assert engine.search("dwd_loan_snapshot")[0]["asset_id"] == "DS000001"
