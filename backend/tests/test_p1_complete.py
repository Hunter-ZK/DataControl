from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def login(username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["accessToken"]


def test_local_auth_and_application_data():
    token = login("demo", "DataControl123!")
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "demo"

    favorites = client.get("/api/v1/activity/favorites", headers=headers)
    assert favorites.status_code == 200
    assert len(favorites.json()["data"]) >= 1

    history = client.get("/api/v1/activity/search-history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["data"]) >= 1


def test_asset_detail_contracts():
    tables = client.get("/api/v1/tables?limit=1")
    assert tables.status_code == 200
    asset_id = tables.json()["data"][0]["assetId"]

    columns = client.get(f"/api/v1/columns?dataset_id={asset_id}")
    assert columns.status_code == 200
    assert len(columns.json()["data"]) >= 1

    assert client.get(f"/api/v1/tables/{asset_id}/tags").status_code == 200
    assert client.get(f"/api/v1/tables/{asset_id}/changes").status_code == 200
    assert client.get(f"/api/v1/tables/{asset_id}/common-sql").status_code == 200
    assert client.get(f"/api/v1/relations/tables/{asset_id}").status_code == 200


def test_activity_write_and_admin_audit():
    token = login("demo", "DataControl123!")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"assetType": "TABLE", "assetId": "DS000001"}

    assert client.post("/api/v1/activity/views", json=payload, headers=headers).status_code == 200
    assert client.post("/api/v1/activity/search-history", json={"keyword": "贷款余额"}, headers=headers).status_code == 200

    admin_token = login("admin", "DataControlAdmin123!")
    audit = client.get("/api/v1/activity/audit", headers={"Authorization": f"Bearer {admin_token}"})
    assert audit.status_code == 200
    assert len(audit.json()["data"]) >= 1
