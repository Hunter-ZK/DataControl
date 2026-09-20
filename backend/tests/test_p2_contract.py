from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_p2_system_phase_and_field_detail_contract():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["phase"] == "P2"

    info = client.get("/api/v1/system/info")
    assert info.status_code == 200
    assert info.json()["data"]["phase"] == "P2"

    tables = client.get("/api/v1/tables?limit=1")
    asset_id = tables.json()["data"][0]["assetId"]
    columns = client.get(f"/api/v1/columns?dataset_id={asset_id}")
    field = columns.json()["data"][0]

    detail = client.get(f"/api/v1/columns/{field['assetId']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["datasetId"] == asset_id
    assert detail.json()["data"]["columnName"] == field["columnName"]


def test_unknown_field_and_unknown_api_return_404():
    assert client.get("/api/v1/columns/FD_DOES_NOT_EXIST").status_code == 404
    assert client.get("/api/v1/not-a-real-route").status_code == 404
