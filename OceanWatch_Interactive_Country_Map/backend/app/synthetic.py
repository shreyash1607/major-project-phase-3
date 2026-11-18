"""Synthetic demo scenes so the app runs with NO downloads. Replace with Copernicus ingestion for real data."""
import numpy as np
RNG = np.random.default_rng(7)
REGIONS = [  # name, lon0, lat0 (top-left), wind
    ("Gulf of Mexico", -90.5, 28.6, 6.0), ("Arabian Sea, off Gujarat", 69.0, 21.2, 2.2),
    ("Bay of Bengal", 87.0, 17.5, 7.5), ("Mediterranean, off Crete", 24.2, 35.6, 5.0),
    ("North Sea", 3.1, 56.0, 12.0)]
RES = 0.0009  # ~100 m pixels for the demo

def sar_scene(n=400, slicks=2):
    img = 10 * np.log10(RNG.gamma(8, 1 / 8, (n, n)) * 0.016)  # speckled sea, ~ -18 dB
    for _ in range(slicks):
        y, x = RNG.integers(60, n - 60, 2); L, W = RNG.integers(40, 80), RNG.integers(5, 12)
        yy, xx = np.mgrid[:n, :n]
        img[((yy - y) / L) ** 2 + ((xx - x) / W) ** 2 < 1] -= RNG.uniform(5, 8)
    return img

def msi_scene(n=300, streaks=2):
    f = lambda m: np.clip(RNG.normal(m, 0.002, (n, n)), 0, 1)
    b = dict(B4=f(0.03), B6=f(0.02), B8=f(0.015), B11=f(0.01))
    for _ in range(streaks):
        y, x = RNG.integers(30, n - 30, 2); h, w = RNG.integers(3, 6), RNG.integers(12, 25)
        b["B8"][y:y + h, x:x + w] += 0.05; b["B11"][y:y + h, x:x + w] += 0.02
    return b
