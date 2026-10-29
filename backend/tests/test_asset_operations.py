from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_complete_columns_contract():
    rows = client.get("/api/v1/tables?limit=1").json()["data"]
    assert rows
    asset_id = rows[0]["assetId"]
    result = client.get(f"/api/v1/tables/{asset_id}/columns/complete")
    assert result.status_code == 200
    payload = result.json()["data"]
    assert payload["assetId"] == asset_id
    assert payload["complete"] is True
    assert payload["total"] == len(payload["items"])
    assert [x["ordinalNo"] for x in payload["items"]] == sorted(x["ordinalNo"] for x in payload["items"])
    assert client.get("/api/v1/tables/no_such_asset/columns/complete").status_code == 404


def test_reverse_reference_counts_are_truthful():
    for endpoint, kind, code in [("/api/v1/code-tables", "CODE_TABLE", "codeTableNo"),
                                  ("/api/v1/data-standards", "STANDARD", "standardNo"),
                                  ("/api/v1/stat-systems", "STAT_SYSTEM", "code")]:
        response = client.get(endpoint)
        assert response.status_code == 200
        rows = response.json()["data"]
        if not rows:
            continue
        asset_id = rows[0]["assetId"]
        refs = client.get("/api/v1/agent-assets/references",
                          params={"asset_type": kind, "asset_id": asset_id, "limit": 1})
        assert refs.status_code == 200
        payload = refs.json()["data"]
        assert payload["total"] >= len(payload["references"])
        assert payload["status"] == ("truncated" if payload["total"] > len(payload["references"]) else "complete")
