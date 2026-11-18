# OceanWatch: AI-Based Marine Pollution Detection from Satellite Images

Implementation of the framework in *"AI-Based Marine Pollution Detection Using Satellite Images"*:
a Sentinel-1 SAR branch (oil-like features), a Sentinel-2 optical branch (suspected floating debris),
confidence/uncertainty flags, provenance for every alert, a map UI and an **analyst-in-the-loop** review step.

> **Scope honesty (mirrors the paper §4.1):** no trained model or experimental accuracy is claimed.
> The shipped detector is a physics/rule-based **baseline** (paper §4.3 baseline i) running on **synthetic** scenes.
> Outputs are *candidates*, never confirmed pollution.

## Structure
```
marine-pollution-detection/
├── backend/     FastAPI service + detection pipeline (app/pipeline.py, synthetic.py, service.py, main.py)
├── frontend/    Leaflet map UI (index.html, css/, js/): no build step
├── database/    schema.sql · mpd.sqlite is created on first run
├── models/      trained weights + metadata (empty: baseline is rule-based)
├── dataset/     raw/ processed/ labels/ (see dataset/README.md)
├── tests/       pytest suite (run from repo root: `pytest`)
├── docs/        ARCHITECTURE.md (paper → code map), API.md, ROADMAP.md
└── README.md
```

## Quick start
**Easiest:** double-click `run.bat` (Windows) or run `./run.sh`. It sets everything up and opens http://localhost:8000.

**Manual:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                          # then open http://localhost:8000
cd .. && pytest                                        # run tests from repo root
```
The DB seeds itself with 10 synthetic scenes on first start. "Reset demo" in the UI regenerates them.

## UI features
Interactive global map with country boundary selector, click-to-inspect location search radius, nearby candidate lookup, and alert footprints coloured by pollutant · confidence & status filters · per-alert provenance
(product ID, sensor, preprocessing/model version, wind, cloud) · uncertainty flags · Confirm / Reject /
Needs-field-check workflow with notes · GeoJSON export for GIS · live stats incl. false alarms per scene.

## Limitations
Rule thresholds are untuned for real data; footprints are bounding boxes; confidence is **not calibrated**;
no real Copernicus ingestion yet (see `docs/ROADMAP.md`). Do not use for regulatory claims without validation.

## Interactive country and location explorer
The monitoring map now includes a country selector (Natural Earth country boundaries), country zoom/filtering, and click-to-inspect search. Click a point on the map and choose a radius (50–1,000 km) to find catalogue alerts near that location. The backend endpoint is `GET /api/inspect?lat=<lat>&lon=<lon>&radius_km=<radius>`. It returns only stored alerts within the selected radius and does not invent a detection when no record exists. Country boundaries and basemap tiles are loaded from external map services, so an internet connection is required for the map experience.
