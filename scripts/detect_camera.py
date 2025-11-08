#!/usr/bin/env python3
"""Detect Jetson CSI camera (Argus) and suggest how to view it.

- Verifies GStreamer Argus availability (nvarguscamerasrc) and attempts to open
  a CSI capture pipeline. Prints a concise recommendation for using camera_stream.py.

Usage
-----
  python3 scripts/detect_camera.py            # human-readable summary
  python3 scripts/detect_camera.py --json     # machine-readable JSON
"""

import argparse
import json
import subprocess
import sys
import cv2


def which(cmd):
    from shutil import which as _which

    return _which(cmd) is not None


def probe_csi(width=1280, height=720, fps=30):
    gst_present = which("gst-inspect-1.0")
    if gst_present:
        # Confirm Argus plugin exists
        try:
            r = subprocess.run(
                ["gst-inspect-1.0", "nvarguscamerasrc"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=3,
            )
            if r.returncode != 0:
                gst_present = False
        except Exception:
            gst_present = False

    can_open = False
    if gst_present:
        pipeline = (
            "nvarguscamerasrc ! "
            f"video/x-raw(memory:NVMM), width={width}, height={height}, framerate={fps}/1 "
            "! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
        )
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            can_open = cap.isOpened()
            cap.release()
        except Exception:
            can_open = False
    return {"gst_present": gst_present, "can_open": can_open}


def recommend(csi):
    if csi["gst_present"]:
        return "python3 scripts/camera_stream.py --width 1280 --height 720 --fps 30 --port 8080"
    return "GStreamer Argus not found. Ensure Jetson drivers and Argus are available."


def main(argv):
    ap = argparse.ArgumentParser(description="Detect CSI camera and usage recommendation")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = ap.parse_args(argv)

    csi_info = probe_csi()
    rec = recommend(csi_info)

    payload = {"csi": csi_info, "recommendation": rec}

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("== CSI (Argus) ==")
    print(f"- GStreamer Argus present: {csi_info['gst_present']}")
    print(f"- Can open nvarguscamerasrc: {csi_info['can_open']}")
    print(f"\n== How to view ==\n- {rec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
