"""
Generate mock predictions using an untrained PointNet++ model.
This lets the full pipeline (convert → animate) run end-to-end
without requiring the trained checkpoint file.
"""

import sys
from pathlib import Path

# Add the pipeline directory to sys.path so imports work
PIPELINE_DIR = Path(__file__).resolve().parent / "lidar_inference_pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

import numpy as np
import torch

from preprocessing.lidar_loader import load_lidar_file
from preprocessing.preprocess import preprocess_lidar
from models.pointnet_model import PointNetPlusPlusSegmentation

# ============================================================
# CONFIGURATION
# ============================================================
NUM_POINTS = 32768
NUM_CLASSES = 3
INPUT_FEATURES = 2
MAX_FRAMES = 10  # Process first 10 frames for a quick demo

# ============================================================
# PATHS (same as main.py uses)
# ============================================================
RAW_DATA_DIR = PIPELINE_DIR / "data" / "raw"
PREDICTION_DIR = PIPELINE_DIR / "data" / "processed" / "predictions"
PREDICTION_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# DEVICE
# ============================================================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("\n" + "=" * 65)
print("MOCK PREDICTION GENERATOR (Untrained Model)")
print("=" * 65)
print(f"\nDevice: {device}")
print(f"Points per frame: {NUM_POINTS}")
print(f"Max frames: {MAX_FRAMES}")

# ============================================================
# FIND RAW LIDAR FILES
# ============================================================
lidar_files = sorted(RAW_DATA_DIR.glob("*.pcd.bin"))[:MAX_FRAMES]

if len(lidar_files) == 0:
    raise FileNotFoundError(f"\nNo .pcd.bin files found in:\n{RAW_DATA_DIR}")

print(f"\nFound {len(lidar_files)} raw LiDAR file(s) to process.")

# ============================================================
# CREATE UNTRAINED MODEL
# ============================================================
print("\nCreating fresh (untrained) PointNet++ model...")
model = PointNetPlusPlusSegmentation(
    num_classes=NUM_CLASSES,
    input_features=INPUT_FEATURES
)
model = model.to(device)
model.eval()
print("Model created (random weights — labels will not be semantically accurate).")

# ============================================================
# PROCESS EACH FRAME
# ============================================================
successful = 0
failed = 0

for idx, file_path in enumerate(lidar_files, start=1):
    print(f"\n--- Frame [{idx}/{len(lidar_files)}]: {file_path.name}")

    try:
        # Load raw LiDAR
        raw_points = load_lidar_file(file_path)
        print(f"  Raw points: {raw_points.shape}")

        # Preprocess (returns real_points, model_points)
        real_points, model_points = preprocess_lidar(raw_points, num_points=NUM_POINTS)

        # Run inference with untrained model
        points_tensor = torch.from_numpy(model_points).float().unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(points_tensor)
            predictions = torch.argmax(outputs, dim=1).squeeze(0).cpu().numpy()

        # Save in the exact format the pipeline expects
        base_name = file_path.name
        if base_name.endswith(".pcd.bin"):
            base_name = base_name[:-8]

        output_path = PREDICTION_DIR / f"{base_name}_prediction.npz"

        np.savez_compressed(
            output_path,
            points=real_points,
            model_points=model_points,
            labels=predictions,
            source_file=file_path.name
        )

        print(f"  [OK] Saved: {output_path.name}")
        successful += 1

    except Exception as e:
        print(f"  [FAIL] ERROR: {e}")
        failed += 1

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 65)
print("MOCK PREDICTION GENERATION COMPLETE")
print("=" * 65)
print(f"  Successful: {successful}")
print(f"  Failed:     {failed}")
print(f"  Output dir: {PREDICTION_DIR}")
print("=" * 65)
