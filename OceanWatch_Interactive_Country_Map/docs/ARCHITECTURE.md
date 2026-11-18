# Architecture

```
Sentinel-1 / Sentinel-2 scene ─► preprocessing ─► detector (per sensor) ─► candidates + flags
                                                                          │
 context (wind, cloud) ───────────────────────────────────────────────────┤
                                                                          ▼
                       SQLite (scenes, alerts, provenance) ◄─ service.py ─► FastAPI ─► Leaflet UI ─► analyst review
```

| Paper section | Implementation |
|---|---|
| §3.1 Data (S1, S2, context) | `scenes` table: sensor, product_id, wind, cloud · `synthetic.py` stands in for downloads |
| §3.2 Preprocessing | `pipeline.py`: mild median despeckle (heavy smoothing erases narrow slicks); cloud suppression |
| §3.3.1 Oil-slick module | `detect_oil_like`: dark formation vs. local background; wind-based look-alike penalty |
| §3.3.2 Debris module | `detect_debris`: FDI-style index + NDVI seaweed flag; sub-pixel warning always attached |
| §3.3.3 Temporal / fusion | **Not yet implemented** (ROADMAP); sensors are shown separately, never blindly merged |
| §3.4 Evaluation | `/api/stats` exposes false alarms per scene; offline metrics belong in ROADMAP |
| §3.5 UI & provenance | Frontend + `alerts`/`scenes` columns (model_version, preprocessing_version, status) |
| §4.4 Human-in-the-loop | `PATCH /api/alerts/{id}/review` |

**Swap-in point for deep learning:** replace the thresholding in `detect_oil_like` / `detect_debris` with a U-Net
probability mask; keep `_objects()` (mask → polygons/flags/confidence) and the DB/API contract unchanged.
