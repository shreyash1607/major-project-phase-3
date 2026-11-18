import json, datetime as dt
from . import db, pipeline as P, synthetic as S

def run_demo(reset=True):
    db.init()
    with db.conn() as c:
        if reset: c.executescript("DELETE FROM alerts; DELETE FROM scenes;")
        now = dt.datetime.now(dt.timezone.utc)
        for i, (name, lon, lat, wind) in enumerate(S.REGIONS):
            for sensor, days in (("Sentinel-1 SAR", i), ("Sentinel-2 MSI", i + 1)):
                cloud = round(float(S.RNG.uniform(0, 0.5)), 2) if "MSI" in sensor else 0.0
                when = (now - dt.timedelta(days=days * 2 + (1 if "MSI" in sensor else 0))).isoformat(timespec="seconds")
                pid = f"SYN_{'S1' if 'SAR' in sensor else 'S2'}_{i}_{when[:10]}"
                sid = c.execute("INSERT INTO scenes(product_id,sensor,region,acquired_at,cloud_fraction,wind_ms,preprocessing_version) VALUES(?,?,?,?,?,?,?)",
                                (pid, sensor, name, when, cloud, wind, P.PREPROC_VERSION)).lastrowid
                geo = (lon, lat, S.RES)
                objs = (P.detect_oil_like(S.sar_scene(), geo, wind) if "SAR" in sensor
                        else P.detect_debris(S.msi_scene(), geo, cloud))
                for o in objs:
                    c.execute("INSERT INTO alerts(scene_id,kind,lat,lon,area_km2,confidence,flags,polygon,model_version) VALUES(?,?,?,?,?,?,?,?,?)",
                              (sid, o["kind"], o["lat"], o["lon"], round(o["area_km2"], 3), o["confidence"],
                               json.dumps(o["flags"]), json.dumps(o["polygon"]), P.MODEL_VERSION))
