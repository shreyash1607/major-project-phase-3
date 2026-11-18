"""Detection pipeline (paper §3.2-3.3). Rule-based BASELINE (paper §4.3 baseline i).
`segment_*` is the swap-in point for a trained U-Net; outputs stay "candidates", never confirmed pollution."""
import numpy as np
from scipy import ndimage as ndi

MODEL_VERSION = "baseline-rules-0.1"
PREPROC_VERSION = "synthetic-calibrated-db-v1"
KM_PER_DEG = 111.32

def _sigmoid(x): return 1 / (1 + np.exp(-x))

def _objects(mask, score_img, geo, kind, min_px, extra_flags, conf_fn):
    lab, n = ndi.label(mask)
    out = []
    lon0, lat0, res = geo  # top-left origin, degrees per pixel
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < min_px: continue
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        elong = max(y1 - y0, x1 - x0) / max(1, min(y1 - y0, x1 - x0))
        flags = list(extra_flags)
        conf, f = conf_fn(float(score_img[ys, xs].mean()), elong)
        flags += f
        lat_c = lat0 - res * ys.mean()
        px_km2 = (res * KM_PER_DEG) ** 2 * np.cos(np.radians(lat_c))
        ring = [[lon0 + res * x0, lat0 - res * y0], [lon0 + res * x1, lat0 - res * y0],
                [lon0 + res * x1, lat0 - res * y1], [lon0 + res * x0, lat0 - res * y1], [lon0 + res * x0, lat0 - res * y0]]
        out.append(dict(kind=kind, lat=float(lat_c), lon=float(lon0 + res * xs.mean()),
                        area_km2=float(len(ys) * px_km2), confidence=round(float(conf), 3), flags=flags,
                        polygon={"type": "Polygon", "coordinates": [ring]}))  # bbox footprint (documented simplification)
    return out

def detect_oil_like(vv_db, geo, wind_ms, min_px=40):
    """Sentinel-1: dark formation vs. local background. Wind outside ~3-10 m/s => look-alike risk (paper §1.1, §3.3.1)."""
    vv = ndi.median_filter(vv_db, 3)  # mild despeckle; heavy smoothing would erase narrow slicks (§3.2)
    contrast = ndi.uniform_filter(vv, 41) - vv
    mask = ndi.binary_opening(contrast > 3.0)
    flags = ["low_wind_lookalike_risk"] if wind_ms < 3 else ["high_wind_unreliable"] if wind_ms > 10 else []
    wind_factor = 0.55 if flags else 1.0
    def conf(c, elong):
        f = ["compact_shape_biogenic_film_possible"] if elong < 1.6 else []
        return float(_sigmoid((c - 3.5) / 1.2) * wind_factor * (0.85 if f else 1.0)), f
    return _objects(mask, contrast, geo, "oil_like", min_px, flags, conf)

def detect_debris(bands, geo, cloud_fraction, min_px=6):
    """Sentinel-2: Floating Debris Index style anomaly + NDVI to separate seaweed-like objects (paper §3.3.2)."""
    if cloud_fraction > 0.4: return []  # suppress when quality masks say interpretation is unreliable
    b4, b6, b8, b11 = (bands[k] for k in ("B4", "B6", "B8", "B11"))
    fdi = b8 - (b6 + (b11 - b6) * ((832 - 740) / (1613 - 740)) * 10)
    ndvi = (b8 - b4) / (b8 + b4 + 1e-6)
    mask = ndi.binary_opening(fdi > 0.012)
    flags = ["partial_cloud_cover"] if cloud_fraction > 0.15 else []
    def conf(v, elong):
        return float(_sigmoid((v - 0.02) / 0.01) * (0.8 if flags else 1.0)), []
    objs = _objects(mask, fdi, geo, "suspected_debris", min_px, flags, conf)
    for o in objs:
        lat_ok = ndvi.mean() > 0.15
        if lat_ok: o["flags"].append("vegetation_signal_seaweed_possible")
        o["flags"].append("sub_pixel_mixing_composition_unconfirmed")
    return objs
