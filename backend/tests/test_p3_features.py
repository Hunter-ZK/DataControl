from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_p3_runtime_contract_is_exposed_for_local_acceptance():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "P3"
    assert data["runtimeContract"] == "embedded-agent-gateway-v1"


def test_unified_search_returns_facets_and_reference_assets():
    response = client.get("/api/v1/search", params={"q": "行政区划", "limit": 50})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 1
    assert any(
        item["assetType"] in {"STANDARD", "CODE_TABLE", "COLUMN"}
        for item in data["items"]
    )

    suggestion = client.get(
        "/api/v1/search/suggest",
        params={"q": "region", "limit": 8},
    )
    assert suggestion.status_code == 200
    assert len(suggestion.json()["data"]) >= 1


def test_relation_graph_path_and_impact_contract():
    graph = client.get(
        "/api/v1/relations/graph/DS000001",
        params={"depth": 2, "direction": "both"},
    )
    assert graph.status_code == 200
    graph_data = graph.json()["data"]
    assert graph_data["centerAssetId"] == "DS000001"
    assert len(graph_data["edges"]) >= 1

    path = client.get(
        "/api/v1/relations/path",
        params={"source": "DS000001", "target": "DS000004", "max_depth": 8},
    )
    assert path.status_code == 200
    assert path.json()["data"]["found"] is True

    impact = client.get(
        "/api/v1/relations/impact/DS000001",
        params={"depth": 3},
    )
    assert impact.status_code == 200
    assert impact.json()["data"]["impactCount"] >= 1


def test_agent_bridge_is_implemented_but_runtime_is_fail_closed_when_not_started():
    status = client.get("/api/v1/agent/status")
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["sqlExecutionEnabled"] is False
    assert data["hiddenReasoningExposed"] is False
    assert data["mode"] == "embedded-monorepo"
    assert data["source"] == "DataControl/agent"
    assert data["sourceMigrated"] is True
    assert data["sessionBridgeImplemented"] is True
    assert data["integrated"] is False
    assert data["realModelAccepted"] is False
    assert data["ready"] is False
    assert "gateway is not reachable" in data["reason"]

    query = client.post(
        "/api/v1/agent/query",
        json={"question": "生成贷款余额 SQL"},
    )
    assert query.status_code == 503
