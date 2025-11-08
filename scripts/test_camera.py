#!/usr/bin/env python3
"""Capture a single frame from the Jetson CSI camera (nvarguscamerasrc)."""
import os
import sys
from pathlib import Path
import cv2

WIDTH = int(os.getenv("CSI_WIDTH", "1280"))
HEIGHT = int(os.getenv("CSI_HEIGHT", "720"))
FPS = int(os.getenv("CSI_FPS", "30"))
SENSOR_ID = int(os.getenv("CSI_SENSOR_ID", "0"))
SENSOR_MODE = os.getenv("CSI_SENSOR_MODE")
SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", "notebooks/camera_snapshot.jpg"))

mode = f" sensor-mode={SENSOR_MODE}" if SENSOR_MODE else ""
pipeline = (
    f"nvarguscamerasrc sensor-id={SENSOR_ID}{mode} ! "
    f"video/x-raw(memory:NVMM), width={WIDTH}, height={HEIGHT}, framerate={FPS}/1 "
    "! nvvidconv ! video/x-raw, format=RGBA ! appsink drop=true max-buffers=1 sync=false"
)
print(
    f"[camera-test] Opening CSI pipeline: {WIDTH}x{HEIGHT}@{FPS} sensor-id={SENSOR_ID} sensor-mode={SENSOR_MODE}"
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    sys.exit("[camera-test] Unable to open CSI camera via GStreamer (nvarguscamerasrc)")

ok, frame = cap.read()
cap.release()

if not ok or frame is None:
    sys.exit("[camera-test] Failed to read frame from camera")

# Convert RGBA to BGR before saving
if frame.ndim == 3 and frame.shape[2] == 4:
    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
if not cv2.imwrite(str(SNAPSHOT_PATH), frame):
    sys.exit(f"[camera-test] Unable to write snapshot to {SNAPSHOT_PATH}")

print(f"[camera-test] Snapshot saved to {SNAPSHOT_PATH}")
