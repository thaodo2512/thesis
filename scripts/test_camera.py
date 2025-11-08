#!/usr/bin/env python3
"""Capture a single frame from the Jetson CSI camera (nvarguscamerasrc)."""
import os
import sys
from pathlib import Path
import cv2

WIDTH = int(os.getenv("CSI_WIDTH", "1280"))
HEIGHT = int(os.getenv("CSI_HEIGHT", "720"))
FPS = int(os.getenv("CSI_FPS", "30"))
SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", "notebooks/camera_snapshot.jpg"))

pipeline = (
    "nvarguscamerasrc ! "
    f"video/x-raw(memory:NVMM), width={WIDTH}, height={HEIGHT}, framerate={FPS}/1 "
    "! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
)
print(f"[camera-test] Opening CSI pipeline: {WIDTH}x{HEIGHT}@{FPS}")
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    sys.exit("[camera-test] Unable to open CSI camera via GStreamer (nvarguscamerasrc)")

ok, frame = cap.read()
cap.release()

if not ok or frame is None:
    sys.exit("[camera-test] Failed to read frame from camera")

SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
if not cv2.imwrite(str(SNAPSHOT_PATH), frame):
    sys.exit(f"[camera-test] Unable to write snapshot to {SNAPSHOT_PATH}")

print(f"[camera-test] Snapshot saved to {SNAPSHOT_PATH}")
