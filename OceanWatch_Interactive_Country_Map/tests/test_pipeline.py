import os, tempfile; os.environ["MPD_DB"] = tempfile.mktemp(suffix=".sqlite")
from fastapi.testclient import TestClient
from app import pipeline as P, synthetic as S
from app.main import app

def test_sar_finds_slick_and_flags_low_wind():
    img = S.sar_scene(slicks=2)
    calm = P.detect_oil_like(img, (0, 0, .001), wind_ms=1.5)
    assert calm and all("low_wind_lookalike_risk" in o["flags"] for o in calm)
    assert max(o["confidence"] for o in P.detect_oil_like(img, (0, 0, .001), 6)) > max(o["confidence"] for o in calm)

def test_cloudy_optical_suppressed():
    assert P.detect_debris(S.msi_scene(), (0, 0, .001), cloud_fraction=0.6) == []

def test_api_review_flow():
    with TestClient(app) as c:
        a = c.get("/api/alerts?min_confidence=0.2").json(); assert a
        r = c.patch(f"/api/alerts/{a[0]['id']}/review", json={"status": "confirmed", "analyst_note": "ok"}).json()
        assert r["status"] == "confirmed" and c.get("/api/stats").json()["scenes"] == 10
