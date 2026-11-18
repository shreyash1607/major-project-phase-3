import json, pathlib, datetime as dt, io, base64
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import numpy as np
from PIL import Image, ImageDraw
from . import db, service

app = FastAPI(title="Marine Pollution Detection API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Q = """SELECT a.*, s.product_id, s.sensor, s.region, s.acquired_at, s.cloud_fraction, s.wind_ms,
       s.preprocessing_version, s.is_synthetic FROM alerts a JOIN scenes s ON s.id=a.scene_id"""

@app.on_event("startup")
def _start():
    db.init()
    with db.conn() as c:
        if c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0: service.run_demo(reset=False)

@app.get("/api/alerts")
def alerts(kind: Optional[str] = None, status: Optional[str] = None, min_confidence: float = Query(0, ge=0, le=1),
           since: Optional[str] = None):
    sql, args = Q + " WHERE a.confidence>=?", [min_confidence]
    for col, v in (("a.kind", kind), ("a.status", status)):
        if v: sql += f" AND {col}=?"; args.append(v)
    if since: sql += " AND s.acquired_at>=?"; args.append(since)
    with db.conn() as c: return [db.row(r) for r in c.execute(sql + " ORDER BY a.confidence DESC", args)]

@app.get("/api/alerts/{aid}")
def alert(aid: int):
    with db.conn() as c: r = c.execute(Q + " WHERE a.id=?", (aid,)).fetchone()
    if not r: raise HTTPException(404, "Alert not found")
    return db.row(r)

class Review(BaseModel):
    status: Literal["confirmed", "rejected", "field_check", "pending"]
    analyst_note: str = Field("", max_length=1000)

@app.patch("/api/alerts/{aid}/review")  # analyst-in-the-loop (paper §3.5, §4.4)
def review(aid: int, body: Review):
    with db.conn() as c:
        n = c.execute("UPDATE alerts SET status=?, analyst_note=?, reviewed_at=? WHERE id=?",
                      (body.status, body.analyst_note, dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), aid)).rowcount
    if not n: raise HTTPException(404, "Alert not found")
    return alert(aid)


@app.get("/api/inspect")
def inspect_location(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180), radius_km: float = Query(250, ge=1, le=2000)):
    """Return known candidate alerts near a clicked map location; never synthesize a detection."""
    import math
    rows = alerts(min_confidence=0.0)
    found = []
    for a in rows:
        p1, p2 = math.radians(lat), math.radians(a["lat"])
        dp = math.radians(a["lat"] - lat)
        dl = math.radians(a["lon"] - lon)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        distance = 6371.0 * 2 * math.asin(math.sqrt(h))
        if distance <= radius_km:
            item = dict(a)
            item["distance_km"] = round(distance, 1)
            found.append(item)
    found.sort(key=lambda x: x["distance_km"])
    return {"query": {"lat": lat, "lon": lon, "radius_km": radius_km}, "count": len(found), "alerts": found, "data_note": "The included alert catalogue is synthetic research demo data, not a live global pollution feed."}

@app.get("/api/stats")
def stats():
    with db.conn() as c:
        g = lambda q: [dict(r) for r in c.execute(q)]
        return {"by_kind": g("SELECT kind, COUNT(*) n, ROUND(AVG(confidence),3) avg_conf FROM alerts GROUP BY kind"),
                "by_status": g("SELECT status, COUNT(*) n FROM alerts GROUP BY status"),
                "scenes": c.execute("SELECT COUNT(*) FROM scenes").fetchone()[0],
                "false_alarms_per_scene": c.execute("SELECT ROUND(1.0*SUM(status='rejected')/COUNT(DISTINCT scene_id),2) FROM alerts").fetchone()[0]}

@app.get("/api/export.geojson")
def export(min_confidence: float = 0, kind: Optional[str] = None):
    feats = [{"type": "Feature", "geometry": a["polygon"], "properties": {k: v for k, v in a.items() if k != "polygon"}}
             for a in alerts(kind=kind, min_confidence=min_confidence)]
    return {"type": "FeatureCollection", "features": feats}

@app.post("/api/demo/reset")
def reset(): service.run_demo(reset=True); return {"ok": True}


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Heuristic image screening demo. This is not a trained ML model or scientific validation."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload a JPG, PNG, or other supported image file.")
    raw = await file.read()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image is too large. Maximum upload size is 12 MB.")
    try:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(400, "The uploaded file could not be read as an image.")
    image.thumbnail((1000, 1000))
    arr = np.asarray(image).astype(np.float32)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    brightness = arr.mean(axis=2)
    # Broad visual cues only: dark patches and unusually bright/saturated patches.
    ocean_like = (b > r * 0.85) & (b > g * 0.78)
    dark = ocean_like & (brightness < np.percentile(brightness[ocean_like], 28) if ocean_like.any() else brightness < 45)
    bright = ocean_like & (brightness > np.percentile(brightness[ocean_like], 92) if ocean_like.any() else brightness > 220) & ((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b])) > 28)
    masks = [("oil_like_visual_candidate", dark), ("floating_material_visual_candidate", bright)]
    regions=[]
    from scipy import ndimage as ndi
    h,w=brightness.shape
    for label, mask in masks:
        lab,n=ndi.label(mask)
        for idx in range(1,n+1):
            ys,xs=np.where(lab==idx)
            if len(xs) < max(18, int(h*w*0.00008)): continue
            x0,x1=int(xs.min()),int(xs.max()+1); y0,y1=int(ys.min()),int(ys.max()+1)
            if (x1-x0)*(y1-y0) > h*w*.45: continue
            regions.append({"type":label,"box":{"x":x0/w,"y":y0/h,"width":(x1-x0)/w,"height":(y1-y0)/h},"pixel_fraction":round(len(xs)/(h*w),5),"screening_score":round(min(.95,.35+len(xs)/(h*w)*8),2)})
    preview=image.copy().convert("RGB"); draw=ImageDraw.Draw(preview)
    for reg in regions:
        q=reg["box"]; xy=(int(q["x"]*w),int(q["y"]*h),int((q["x"]+q["width"])*w),int((q["y"]+q["height"])*h))
        draw.rectangle(xy, outline=(255,170,65) if reg["type"].startswith("oil") else (50,210,220), width=3)
    buff=io.BytesIO(); preview.save(buff,format="JPEG",quality=82)
    return {"filename":file.filename,"width":w,"height":h,"regions":regions,"candidate_count":len(regions),"preview_data_url":"data:image/jpeg;base64,"+base64.b64encode(buff.getvalue()).decode(),"method":"visual heuristic screening baseline","is_trained_model":False,"warning":"These are visual candidates only, not verified pollution detections. This endpoint does not use a trained AI model or satellite calibration."}

@app.get("/api/health")
def health(): return {"ok": True}

@app.middleware("http")
async def no_cache(request, call_next):  # always serve the latest frontend files during development
    r = await call_next(request)
    if not request.url.path.startswith("/api"): r.headers["Cache-Control"] = "no-store"
    return r

FRONT = pathlib.Path(__file__).parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")
