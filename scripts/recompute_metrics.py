"""Create an auditable evidence pack from cached LiDAR predictions.

This script intentionally separates values that can be reproduced from the
checked-out data from claims that require unavailable ground truth, model
weights, or a documented baseline. It never copies presentation figures into
the output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the production converter directly. Importing ``perception`` executes
# its package exports, which currently include a stale helper name unrelated to
# metric generation.
from lidar_inference_pipeline.conversion.adaptive_2_5d_converter import Adaptive2_5DConverter


DEFAULT_PREDICTIONS = ROOT / "lidar_inference_pipeline" / "data" / "processed" / "predictions"
DEFAULT_SCENES = ROOT / "config" / "demo_scenes.json"
DEFAULT_OUTPUT = ROOT / "evidence" / "current"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def as_scalar(value: Any) -> Any:
    """Convert NumPy scalar/string values to JSON-safe values."""
    if isinstance(value, np.ndarray) and value.shape == ():
        return value.item()
    if isinstance(value, np.generic):
        return value.item()
    return value


def fixed_fine_occupied_cell_count(points: np.ndarray, resolution: float) -> int:
    """Count occupied cells at a uniform fine resolution, not a dense grid."""
    if len(points) == 0:
        return 0
    x_idx = np.floor(points[:, 0] / resolution).astype(np.int64)
    y_idx = np.floor(points[:, 1] / resolution).astype(np.int64)
    coordinates = np.column_stack((x_idx, y_idx))
    return int(np.unique(coordinates, axis=0).shape[0])


def load_scene_config(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError(f"{path} must contain a non-empty scenes list")
    required = {"id", "prediction_file", "title"}
    for scene in scenes:
        missing = required - set(scene)
        if missing:
            raise ValueError(f"Scene is missing required fields: {sorted(missing)}")
    return scenes


def inspect_frame(path: Path, converter: Adaptive2_5DConverter) -> dict[str, Any]:
    started = time.perf_counter()
    with np.load(path, allow_pickle=False) as data:
        required = {"points", "labels"}
        missing = required - set(data.files)
        if missing:
            raise ValueError(f"missing arrays: {sorted(missing)}")
        points = np.asarray(data["points"])
        labels = np.asarray(data["labels"])
        source_file = as_scalar(data["source_file"]) if "source_file" in data.files else None

    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError(f"points must have shape (N, >=3), got {points.shape}")
    if labels.ndim != 1 or len(labels) != len(points):
        raise ValueError(f"labels must have shape ({len(points)},), got {labels.shape}")
    if not np.isfinite(points[:, :3]).all():
        raise ValueError("points contain NaN or infinity in XYZ")

    distances = np.hypot(points[:, 0], points[:, 1])
    clipped_points = points[distances <= converter.far_distance]
    clipped_labels = labels[distances <= converter.far_distance]
    mapping_started = time.perf_counter()
    mapping = converter.convert(clipped_points, clipped_labels)
    mapping_elapsed_ms = (time.perf_counter() - mapping_started) * 1000

    uniform_count = fixed_fine_occupied_cell_count(clipped_points, converter.near_resolution)
    adaptive_count = int(mapping["total_cells"])
    reduction = ((uniform_count - adaptive_count) / uniform_count * 100) if uniform_count else 0.0
    elapsed_ms = (time.perf_counter() - started) * 1000

    return {
        "prediction_file": path.name,
        "sha256": sha256(path),
        "source_file": str(source_file) if source_file is not None else None,
        "input_point_count": int(len(points)),
        "points_within_60m": int(len(clipped_points)),
        "label_histogram": {str(label): int(count) for label, count in zip(*np.unique(labels, return_counts=True))},
        "adaptive_2_5d_cells": adaptive_count,
        "uniform_fine_occupied_cells": uniform_count,
        "adaptive_cell_reduction_vs_uniform_fine_percent": round(reduction, 4),
        "mapping_only_latency_ms": round(mapping_elapsed_ms, 4),
        "validation_latency_ms": round(elapsed_ms, 4),
    }


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def average(key: str) -> float:
        return round(float(np.mean([row[key] for row in rows])), 4) if rows else 0.0

    semantic_labels_observed = sorted({int(label) for row in rows for label in row["label_histogram"]})
    return {
        "frames_validated": len(rows),
        "average_input_point_count": average("input_point_count"),
        "average_points_within_60m": average("points_within_60m"),
        "average_adaptive_2_5d_cells": average("adaptive_2_5d_cells"),
        "average_uniform_fine_occupied_cells": average("uniform_fine_occupied_cells"),
        "average_adaptive_cell_reduction_vs_uniform_fine_percent": average(
            "adaptive_cell_reduction_vs_uniform_fine_percent"
        ),
        "average_mapping_only_latency_ms": average("mapping_only_latency_ms"),
        "semantic_labels_observed": semantic_labels_observed,
    }


def build_metrics(predictions_dir: Path, scene_config: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scenes = load_scene_config(scene_config)
    converter = Adaptive2_5DConverter()
    all_files = sorted(predictions_dir.glob("*_prediction.npz"))
    if not all_files:
        raise FileNotFoundError(f"No prediction files found in {predictions_dir}")

    frozen_names = {scene["prediction_file"] for scene in scenes}
    missing_frozen = sorted(name for name in frozen_names if not (predictions_dir / name).is_file())
    if missing_frozen:
        raise FileNotFoundError(f"Frozen demo scene files are missing: {missing_frozen}")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for file_path in all_files:
        try:
            row = inspect_frame(file_path, converter)
            row["frozen_demo_scene"] = file_path.name in frozen_names
            rows.append(row)
        except Exception as error:  # keep a full processing ledger rather than hide failures
            failures.append({"prediction_file": file_path.name, "error": str(error)})

    metric_document = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/recompute_metrics.py",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "input": {
            "predictions_directory": str(predictions_dir.relative_to(ROOT)),
            "prediction_files_discovered": len(all_files),
            "frozen_demo_scene_config": str(scene_config.relative_to(ROOT)),
            "frozen_demo_scene_count": len(scenes),
            "label_provenance": {
                "status": "unverified",
                "reason": "Cached prediction files contain no checkpoint hash, ground-truth labels, or evaluation split manifest. This repository's mock generator explicitly uses an untrained PointNet++ model.",
            },
        },
        "mapping_configuration": {
            "range_meters": converter.far_distance,
            "near_resolution_meters": converter.near_resolution,
            "medium_resolution_meters": converter.medium_resolution,
            "far_resolution_meters": converter.far_resolution,
            "baseline_definition": "Uniform fine-grid occupied XY cells at 0.25 m for the same points within 60 m. This is a cell-count baseline, not a sparse-voxel memory baseline.",
        },
        "results": summary(rows),
        "claims": {
            "frame_processing": {
                "status": "recomputed",
                "value": f"{len(rows)} / {len(all_files)} cached prediction files passed schema, finite-XYZ, and adaptive-map conversion checks.",
            },
            "adaptive_cell_reduction": {
                "status": "recomputed",
                "value": "See results.average_adaptive_cell_reduction_vs_uniform_fine_percent.",
                "scope": "Occupied-cell count versus a fixed 0.25 m uniform grid; it is not a memory reduction claim.",
            },
            "semantic_validation_accuracy": {
                "status": "not_available",
                "reason": "No held-out ground-truth labels and split manifest were found in the cached prediction inputs.",
            },
            "semantic_class_coverage": {
                "status": "recomputed" if set(summary(rows)["semantic_labels_observed"]) == {0, 1, 2} else "insufficient",
                "value": summary(rows)["semantic_labels_observed"],
                "reason": "A public semantic-class legend must not imply that all three classes are present unless they are observed in the frozen replay inputs.",
            },
            "sparse_voxel_memory_reduction": {
                "status": "not_available",
                "reason": "No sparse-voxel baseline implementation and serialized-memory measurement protocol are included in this verifier.",
            },
            "dense_voxel_memory_reduction": {
                "status": "not_available",
                "reason": "No dense-voxel dimensions, dtype, and baseline protocol are included in this verifier.",
            },
            "end_to_end_inference_latency": {
                "status": "not_available",
                "reason": "This verifier measures only adaptive-map conversion. It does not execute a trained semantic model.",
            },
            "target_realtime_performance": {
                "status": "target_only",
                "reason": "No optimized inference implementation or benchmark evidence is present in this run.",
            },
        },
        "frames": rows,
        "failures": failures,
    }
    return metric_document, scenes


def write_report(metrics: dict[str, Any], scenes: list[dict[str, str]], output: Path) -> None:
    results = metrics["results"]
    lines = [
        "# Balerion Reproducibility Report",
        "",
        f"Generated: `{metrics['generated_at_utc']}`",
        "",
        "## Verified in this run",
        "",
        f"- Cached predictions discovered: **{metrics['input']['prediction_files_discovered']}**",
        f"- Valid frames: **{results['frames_validated']}**",
        f"- Frozen public-demo scenes: **{len(scenes)}**",
        f"- Average adaptive 2.5D cells: **{results['average_adaptive_2_5d_cells']}**",
        f"- Average uniform fine occupied cells: **{results['average_uniform_fine_occupied_cells']}**",
        f"- Average adaptive cell-count reduction: **{results['average_adaptive_cell_reduction_vs_uniform_fine_percent']}%**",
        f"- Average mapping-only conversion time: **{results['average_mapping_only_latency_ms']} ms/frame**",
        f"- Semantic labels observed in cached predictions: **{results['semantic_labels_observed']}**",
        "",
        "## Important interpretation",
        "",
        "The verified reduction is an occupied-cell count comparison, not a sparse/dense voxel memory claim. Semantic labels are unverified in this evidence pack because the current cached inputs do not include a checkpoint hash, held-out ground truth, or split manifest.",
        "The public UI must also disclose the observed class coverage; it must not promise a three-class semantic replay if the selected cached frames do not contain all three labels.",
        "",
        "## Frozen scenes",
        "",
    ]
    lines.extend(f"- `{scene['prediction_file']}` - {scene['title']}" for scene in scenes)
    lines.extend([
        "",
        "## Unavailable claims",
        "",
        "- Held-out semantic validation accuracy",
        "- Sparse/dense voxel memory reductions",
        "- End-to-end trained-model inference latency",
        "- Real-time performance target",
        "",
        "See `metrics.json` for the machine-readable ledger, frame hashes, measurements, and reasons.",
    ])
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute auditable Balerion prototype metrics.")
    parser.add_argument("--predictions-dir", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--scenes", type=Path, default=DEFAULT_SCENES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    predictions_dir = args.predictions_dir.resolve()
    scene_config = args.scenes.resolve()
    output = args.output.resolve()
    metrics, scenes = build_metrics(predictions_dir, scene_config)
    output.mkdir(parents=True, exist_ok=True)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (output / "demo_scenes.json").write_text(json.dumps({"scenes": scenes}, indent=2) + "\n", encoding="utf-8")
    write_report(metrics, scenes, output)
    print(f"Wrote reproducibility evidence to {output}")
    print(json.dumps(metrics["results"], indent=2))
    return 0 if not metrics["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
