from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_catalog_page_has_true_total_and_filters_before_slice():
    response = client.get("/api/v1/tables/page", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    first = response.json()["data"]
    assert first["total"] >= len(first["items"])
    assert all(item["status"] == "ONLINE" for item in first["items"])
    if first["total"] > 10:
        second = client.get("/api/v1/tables/page", params={"limit": 10, "offset": 10}).json()["data"]
        assert not ({x["assetId"] for x in first["items"]} & {x["assetId"] for x in second["items"]})
    filtered = client.get("/api/v1/tables/page", params={"limit": 10, "keyword": "unlikely___q___"}).json()["data"]
    assert filtered == {"items": [], "total": 0}


def test_search_page_facets_are_complete():
    response = client.get("/api/v1/search/page", params={"q": "贷款", "limit": 5})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == sum(data["facets"].values())
    assert len(data["items"]) <= 5


def test_statistical_system_filter_respects_keyword():
    response = client.get("/api/v1/stat-systems", params={"keyword": "___not_an_existing_stat_code___"})
    assert response.status_code == 200
    assert response.json()["data"] == []
