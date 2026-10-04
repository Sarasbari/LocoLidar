"""Export compact, static replay data for the public Vercel prototype."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lidar_inference_pipeline.conversion.adaptive_2_5d_converter import Adaptive2_5DConverter


PREDICTIONS = ROOT / "lidar_inference_pipeline" / "data" / "processed" / "predictions"
SCENES = ROOT / "config" / "demo_scenes.json"
METRICS = ROOT / "evidence" / "current" / "metrics.json"
OUT = ROOT / "web" / "data"
MAX_DISPLAY_POINTS = 3500


def scalar(value):
    return value.item() if isinstance(value, np.generic) else value


def compact_cell(cell: dict) -> dict:
    layers = cell.get("layers", [])
    label = int(max(layers, key=lambda layer: layer["point_count"])["label"]) if layers else -1
    return {
        "x": int(cell["x_index"]),
        "y": int(cell["y_index"]),
        "r": float(cell["resolution"]),
        "zone": cell["zone"],
        "label": label,
        "z": round(float(cell["height_max"]), 2),
        "n": int(cell["point_count"]),
    }


def main() -> None:
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    config = json.loads(SCENES.read_text(encoding="utf-8"))
    frame_metrics = {frame["prediction_file"]: frame for frame in metrics["frames"]}
    converter = Adaptive2_5DConverter()
    exported = []

    for scene in config["scenes"]:
        prediction_path = PREDICTIONS / scene["prediction_file"]
        expected_hash = frame_metrics[scene["prediction_file"]]["sha256"]
        import hashlib
        actual_hash = hashlib.sha256(prediction_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"Evidence is stale for {prediction_path.name}; rerun recompute_metrics.py first.")

        with np.load(prediction_path, allow_pickle=False) as data:
            points = np.asarray(data["points"])
            labels = np.asarray(data["labels"])
            source_file = scalar(data["source_file"]) if "source_file" in data.files else prediction_path.name
        within_range = np.hypot(points[:, 0], points[:, 1]) <= converter.far_distance
        points, labels = points[within_range], labels[within_range]
        step = max(1, int(np.ceil(len(points) / MAX_DISPLAY_POINTS)))
        display_points = [
            [round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2), int(label)]
            for p, label in zip(points[::step], labels[::step])
        ]
        adaptive_map = converter.convert(points, labels)
        exported.append({
            "id": scene["id"],
            "title": scene["title"],
            "source_file": str(source_file),
            "display_points": display_points,
            "cells": [compact_cell(cell) for cell in adaptive_map["cells"]],
            "metrics": frame_metrics[scene["prediction_file"]],
        })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "demo-data.json").write_text(json.dumps({
        "schema_version": 1,
        "kind": "recorded_replay",
        "notice": "Precomputed recorded replay. Semantic labels are unverified in the current evidence pack; no model runs in the browser.",
        "scenes": exported,
    }, separators=(",", ":")), encoding="utf-8")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(exported)} scenes to {OUT}")


if __name__ == "__main__":
    main()
