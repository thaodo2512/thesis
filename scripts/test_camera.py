#!/usr/bin/env python3
"""Capture a single frame from the JetBot camera for smoke testing."""
import os
import sys
from pathlib import Path
import cv2

VIDEO_DEVICE = os.getenv("VIDEO_DEVICE", "/dev/video0")
SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", "notebooks/camera_snapshot.jpg"))

print(f"[camera-test] Opening video device: {VIDEO_DEVICE}")
cap = cv2.VideoCapture(VIDEO_DEVICE)
if not cap.isOpened():
    sys.exit(f"[camera-test] Unable to open video device {VIDEO_DEVICE}")

ok, frame = cap.read()
cap.release()

if not ok or frame is None:
    sys.exit("[camera-test] Failed to read frame from camera")

SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
if not cv2.imwrite(str(SNAPSHOT_PATH), frame):
    sys.exit(f"[camera-test] Unable to write snapshot to {SNAPSHOT_PATH}")

print(f"[camera-test] Snapshot saved to {SNAPSHOT_PATH}")
