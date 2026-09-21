from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.search.engine import SearchEngine
from backend.app.search.service import SearchService

client = TestClient(app)


def test_search_supports_short_chinese_multi_token_and_complete_pagination(tmp_path: Path):
    engine = SearchEngine(tmp_path / "search.db")
    documents = [
        {
            "asset_id": f"WR{i:06d}",
            "asset_type": "WORD_ROOT",
            "title": f"贷款余额词根{i:03d}",
            "technical_name": f"loan_balance_{i:03d}",
            "body": "贷款 余额 标准词根",
        }
        for i in range(650)
    ]
    engine.rebuild(documents)

    with SessionLocal() as db:
        service = SearchService(db)
        service.engine = engine

        short = service.search("贷款", offset=0, limit=20)
        assert short["total"] == 650
        assert short["facets"]["assetTypes"]["WORD_ROOT"] == 650

        multi = service.search("贷款 余额", offset=600, limit=25)
        assert multi["total"] == 650
        assert multi["offset"] == 600
        assert len(multi["items"]) == 25
        assert all("<mark>" in item["titleHighlight"] for item in multi["items"])


def test_both_direction_relation_does_not_cross_upstream_ancestor_into_sibling_branch():
    response = client.get(
        "/api/v1/relations/graph/DS000004",
        params={"depth": 3, "direction": "both"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    node_ids = {node["assetId"] for node in data["nodes"]}

    # DS000008 / DS000009 are downstream of upstream ancestor DS000002, not
    # downstream of center DS000004. The old one-BFS `both` traversal leaked them.
    assert "DS000008" not in node_ids
    assert "DS000009" not in node_ids
    assert any(node["level"] < 0 for node in data["nodes"])
    assert any(node["level"] > 0 for node in data["nodes"])


def test_field_lineage_api_exposes_upstream_downstream_and_transformation():
    columns_response = client.get(
        "/api/v1/columns",
        params={"dataset_id": "DS000004", "limit": 500},
    )
    assert columns_response.status_code == 200
    columns = columns_response.json()["data"]
    region = next(item for item in columns if item["columnName"] == "region_code")
    loan_balance = next(item for item in columns if item["columnName"] == "loan_balance")

    region_graph = client.get(
        f"/api/v1/relations/columns/{region['assetId']}",
        params={"depth": 2, "direction": "both"},
    )
    assert region_graph.status_code == 200
    region_data = region_graph.json()["data"]
    assert len(region_data["edges"]) >= 1
    assert any(node["level"] < 0 for node in region_data["nodes"])

    table_edges = client.get("/api/v1/relations/fields/table/DS000004")
    assert table_edges.status_code == 200
    table_data = table_edges.json()["data"]
    assert len(table_data["edges"]) >= 1
    assert any(edge["transformation"] for edge in table_data["edges"])

    balance_graph = client.get(
        f"/api/v1/relations/columns/{loan_balance['assetId']}",
        params={"depth": 1, "direction": "upstream"},
    ).json()["data"]
    assert any(
        edge["relationType"] in {"DIRECT", "AGGREGATED"}
        for edge in balance_graph["edges"]
    )
