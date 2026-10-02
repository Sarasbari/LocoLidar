# Run Project Pipeline

## Goal
Successfully set up the environment, run the 3D LiDAR inference pipeline, convert the output to an adaptive 2.5D map, and visualize the results.

## Tasks
- [x] Task 1: Create and activate virtual environment → Verify: `python -c "import sys; print(sys.prefix)"` points to `.venv_cuda`
- [x] Task 2: Install dependencies → Verify: `pip freeze` shows `torch`, `numpy`, `matplotlib` (Note: Used `requirements_no_open3d.txt` to avoid installation issues)
- [x] Task 3: Run Full Inference Pipeline → Verify: Used `generate_mock_predictions.py` (since the `.pth` weights are missing) to output predictions to `data/processed/predictions/`
- [x] Task 4: Convert to Adaptive 2.5D Map → Verify: `python lidar_inference_pipeline/convert_to_adaptive_2_5d.py` successfully generates map grid arrays
- [x] Task 5: Visualize 3D Semantic Point Cloud → Verify: `python lidar_inference_pipeline/animate_raw_3d.py` runs and creates a visualization (GIF)
- [x] Task 6: Run Visualization Dashboard for 2.5D map → Verify: `python lidar_inference_pipeline/animate_adaptive_map.py` runs and outputs the dashboard render

## Done When
- [x] The PointNet++ model runs on the sample point clouds without errors.
- [x] An adaptive 2.5D map is generated from the 3D semantic cloud.
- [x] Visualizations/Animations for both 3D and 2.5D mapping are successfully rendered and saved/displayed.

---

# 🚀 Step-by-Step Execution Guide

This is the exact sequence of commands to execute the pipeline end-to-end on your machine.

### 1. Activate Environment
First, ensure you are in the correct virtual environment where dependencies are installed.
```powershell
.\.venv_cuda\Scripts\activate
```

### 2. Generate Predictions (Inference)
Since the pretrained model checkpoint (`best_weighted_pointnet_model.pth`) is missing from the repository, we use a custom script to generate predictions using a freshly initialized (untrained) model. This allows the rest of the pipeline to run.
```powershell
python generate_mock_predictions.py
```
*(This will process the raw `.pcd.bin` files and output `.npz` files into `lidar_inference_pipeline/data/processed/predictions`)*

### 3. Convert 3D Predictions to 2.5D Maps
Convert the 3D semantic predictions into an adaptive 2.5D grid map format.
```powershell
python lidar_inference_pipeline/convert_to_adaptive_2_5d.py
```
*(This will save the 2.5D maps into `lidar_inference_pipeline/data/processed/adaptive_maps_2_5d`)*

### 4. Generate 3D Animation
Render a visualization of the raw 3D predictions.
```powershell
python lidar_inference_pipeline/animate_raw_3d.py
```
*(This will generate an animated GIF at `lidar_inference_pipeline/data/processed/visualizations/adaptive_raw_3d.gif`)*

### 5. Generate 2.5D Animation
Render the final 2.5D adaptive map dashboard visualization.
```powershell
python lidar_inference_pipeline/animate_adaptive_map.py
```
*(This will generate an animated GIF at `lidar_inference_pipeline/data/processed/visualizations/adaptive_lidar_animation.gif`)*
