# Roadmap (from the paper's Future Work)
1. Copernicus Data Space ingestion + SNAP/rasterio preprocessing (calibration, geocoding, atmospheric correction).
2. Train U-Net models: SAR on public oil-spill masks, optical on MARIDA; scene/region-level splits.
3. Evaluate 3 baselines (rules, RF/SVM, U-Net): precision, recall, F1, IoU, PR curves, false alarms/scene, cross-region.
4. Confidence calibration before alert thresholds are used.
5. Temporal persistence/drift analysis and calibrated sensor fusion.
6. Auth/roles for analysts, audit log, PostGIS, Docker.
