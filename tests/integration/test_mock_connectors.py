from fastapi.testclient import TestClient

from integrations.connectors.mock.mock_connectors import app


client = TestClient(app)


def test_mock_projects_endpoint_returns_paginated_demo_data():
    response = client.get('/projects?page=1&page_size=2')

    assert response.status_code == 200
    body = response.json()
    assert body['pagination']['page_size'] == 2
    assert len(body['data']) == 2


def test_mock_write_endpoint_returns_success_without_persisting():
    response = client.post('/projects', json={'id': 'new', 'name': 'Demo'})

    assert response.status_code == 200
    body = response.json()
    assert body['success'] is True
    assert body['persisted'] is False
