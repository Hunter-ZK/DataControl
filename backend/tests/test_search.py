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


def test_search_page_returns_true_total_and_filtered_facets(tmp_path: Path):
    engine = SearchEngine(tmp_path / "search_page.db")
    engine.rebuild([
        {"asset_id": "DS1", "asset_type": "TABLE", "title": "贷款余额日快照",
         "technical_name": "dwd_loan", "body": "贷款余额"},
        {"asset_id": "FD1", "asset_type": "COLUMN", "title": "贷款余额",
         "technical_name": "loan_amt", "body": "贷款余额字段"},
    ])
    result = engine.search_page("贷款", limit=1)
    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["facets"] == {"TABLE": 1, "COLUMN": 1}
    next_page = engine.search_page("贷款", offset=1, limit=1)
    assert next_page["items"][0]["asset_id"] != result["items"][0]["asset_id"]
    fields = engine.search_page("贷款", asset_type="COLUMN")
    assert fields["total"] == 1
    assert fields["items"][0]["asset_type"] == "COLUMN"
