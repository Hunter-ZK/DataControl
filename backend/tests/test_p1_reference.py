from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_home_overview_contract():
    response = client.get('/api/v1/home/overview')
    assert response.status_code == 200
    data = response.json()['data']
    assert 'tableCount' in data
    assert 'columnCount' in data
    assert 'layers' in data


def test_reference_collections_are_available():
    for path in ['/api/v1/catalogs', '/api/v1/code-tables', '/api/v1/data-standards', '/api/v1/word-roots', '/api/v1/metrics', '/api/v1/stat-systems']:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.json()['code'] == 'OK'


def test_relation_endpoint_rejects_unknown_asset():
    response = client.get('/api/v1/relations/tables/DS999999')
    assert response.status_code == 404
