# models/
Place trained weights here (e.g. `sar_unet_v1.pt`, `msi_unet_v1.pt`) with a sidecar `*.json`
recording training data version, split, metrics and calibration (paper §3.5: model versions are logged per alert).

**Status:** empty. No model has been trained; the app uses the rule-based baseline in `backend/app/pipeline.py`.
Plug-in point: `detect_oil_like` / `detect_debris` (replace thresholding with a U-Net probability mask).
