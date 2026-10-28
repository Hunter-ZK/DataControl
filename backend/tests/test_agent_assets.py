"""Asset facts are resolved by real primary keys, never by model-invented IDs."""
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_asset_lookup_and_navigation_contract():
    r = client.get("/api/v1/agent-assets/TABLE/DS000001")
    assert r.status_code == 200
    item = r.json()["data"]
    assert item["assetType"] == "TABLE"
    assert item["assetId"] == "DS000001"
    assert item["title"]
    assert item["technicalName"]
    assert isinstance(item["details"], dict)


def test_unknown_asset_id_fails_closed():
    response = client.get("/api/v1/agent-assets/TABLE/DS999999")
    assert response.status_code == 404
    response = client.get("/api/v1/agent-assets/ARBITRARY/DS000001")
    assert response.status_code == 422


def test_lineage_summary_contains_only_recorded_edges():
    r = client.get("/api/v1/agent-assets/lineage/TABLE/DS000001", params={"depth": 2})
    assert r.status_code == 200
    payload = r.json()["data"]
    assert payload["assetId"] == "DS000001"
    assert len(payload["edges"]) >= 1
    for edge in payload["edges"]:
        assert edge["srcAssetId"]
        assert edge["dstAssetId"]
        assert edge["evidence"]


def test_reference_response_does_not_invent_associations():
    r = client.get("/api/v1/agent-assets/references",
                   params={"asset_type": "TABLE", "asset_id": "DS000001"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["references"] == []
    assert data["status"] == "unsupported_relationship"
