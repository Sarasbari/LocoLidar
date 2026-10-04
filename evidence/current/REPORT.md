# Balerion Reproducibility Report

Generated: `2026-10-04T05:03:11.498377+00:00`

## Verified in this run

- Cached predictions discovered: **10**
- Valid frames: **10**
- Frozen public-demo scenes: **3**
- Average adaptive 2.5D cells: **4029.4**
- Average uniform fine occupied cells: **4935.8**
- Average adaptive cell-count reduction: **18.3116%**
- Average mapping-only conversion time: **180.0305 ms/frame**
- Semantic labels observed in cached predictions: **[2]**

## Important interpretation

The verified reduction is an occupied-cell count comparison, not a sparse/dense voxel memory claim. Semantic labels are unverified in this evidence pack because the current cached inputs do not include a checkpoint hash, held-out ground truth, or split manifest.
The public UI must also disclose the observed class coverage; it must not promise a three-class semantic replay if the selected cached frames do not contain all three labels.

## Frozen scenes

- `n008-2018-08-01-15-16-36-0400__LIDAR_TOP__1533151603547590_prediction.npz` - Recorded LiDAR Scene 01
- `n008-2018-08-01-15-16-36-0400__LIDAR_TOP__1533151604048025_prediction.npz` - Recorded LiDAR Scene 02
- `n008-2018-08-01-15-16-36-0400__LIDAR_TOP__1533151604547893_prediction.npz` - Recorded LiDAR Scene 03

## Unavailable claims

- Held-out semantic validation accuracy
- Sparse/dense voxel memory reductions
- End-to-end trained-model inference latency
- Real-time performance target

See `metrics.json` for the machine-readable ledger, frame hashes, measurements, and reasons.
