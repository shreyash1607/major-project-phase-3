from fastapi.testclient import TestClient
from app.main import app


def test_inspect_returns_nearby_catalogue_alerts():
    with TestClient(app) as client:
        alerts = client.get('/api/alerts').json()
        assert alerts
        first = alerts[0]
        response = client.get('/api/inspect', params={
            'lat': first['lat'], 'lon': first['lon'], 'radius_km': 50
        })
        assert response.status_code == 200
        data = response.json()
        assert data['count'] >= 1
        assert data['alerts'][0]['distance_km'] == 0.0


def test_inspect_empty_area_does_not_invent_alerts():
    with TestClient(app) as client:
        response = client.get('/api/inspect', params={
            'lat': 0, 'lon': 0, 'radius_km': 10
        })
        assert response.status_code == 200
        assert response.json()['count'] == 0
