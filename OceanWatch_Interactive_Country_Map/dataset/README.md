# dataset/
```
raw/        downloaded Sentinel-1 GRD / Sentinel-2 L2A products (Copernicus Data Space) and MARIDA patches
processed/  calibrated, geocoded, tiled arrays
labels/     expert masks + label-confidence + look-alike / confirmed-negative flags (paper §3.1)
```
Split by **scene / geography**, never by random tile (paper §3.4). Large files are git-ignored.
