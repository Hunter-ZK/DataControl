from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_system_info_disables_external_research_for_p2():
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["developmentIncrement"] == "Next-P2"
    assert data["externalResearchEnabled"] is False
    assert data["sqlExecutionEnabled"] is False


def test_semantic_metric_detail_exposes_time_dimensions_and_internal_policy():
    response = client.get("/api/v1/semantic/metrics/metric_loan_balance")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metricCode"] == "metric_loan_balance"
    assert data["metricKind"] == "BASE"
    assert data["source"]["assetId"] == "DS000004"
    assert data["time"]["field"] == "stat_month"
    assert data["time"]["additivity"] == "NON_ADDITIVE"
    assert data["time"]["latestStrategy"] == "MAX"
    assert data["researchPolicy"] == "internal_only"
    assert any(item["name"] == "region_code" for item in data["validDimensions"])
    assert any(item.get("field") == "currency_cd" for item in data["mandatoryFilters"])


def test_p2_ratio_and_derived_metrics_are_persisted_as_governed_assets():
    ratio = client.get("/api/v1/semantic/metrics/metric_npl_ratio")
    yoy = client.get("/api/v1/semantic/metrics/metric_loan_balance_yoy")
    assert ratio.status_code == 200
    assert yoy.status_code == 200

    ratio_data = ratio.json()["data"]
    assert ratio_data["metricKind"] == "RATIO"
    assert ratio_data["numeratorMetricCode"] == "metric_npl_balance"
    assert ratio_data["denominatorMetricCode"] == "metric_loan_balance"
    assert ratio_data["formula"]

    yoy_data = yoy.json()["data"]
    assert yoy_data["metricKind"] == "DERIVED"
    assert "贷款增长" in yoy_data["aliases"]
    assert yoy_data["formula"]


def test_metrics_list_includes_semantic_model_v2_fields_for_agent_loader():
    response = client.get("/api/v1/metrics", params={"keyword": "不良贷款率"})
    assert response.status_code == 200
    rows = response.json()["data"]
    row = next(item for item in rows if item["metricCode"] == "metric_npl_ratio")
    assert row["metricKind"] == "RATIO"
    assert row["timeGrain"] == "MONTH"
    assert row["latestStrategy"] == "MAX"
    assert row["mandatoryFilters"]
