# REST API (interactive docs at `/docs`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/alerts?kind=&status=&min_confidence=&since=` | Filtered alerts, highest confidence first |
| GET | `/api/alerts/{id}` | Alert with scene provenance |
| PATCH | `/api/alerts/{id}/review` | Body `{status: confirmed\|rejected\|field_check\|pending, analyst_note}` |
| GET | `/api/stats` | Counts by kind/status, scenes, false alarms per scene |
| GET | `/api/export.geojson?min_confidence=&kind=` | FeatureCollection for GIS |
| POST | `/api/demo/reset` | Regenerate synthetic demo data |
