#!/usr/bin/env python3
"""Detect camera type on Jetson and suggest how to use it.

- Enumerates V4L2 devices (/dev/video*) and reports driver/card info.
- Checks for GStreamer Argus (CSI) support and attempts to open it.
- Prints a concise recommendation for using camera_stream.py.

Usage
-----
  python3 scripts/detect_camera.py            # human-readable summary
  python3 scripts/detect_camera.py --json     # machine-readable JSON

Run inside the dev container with hardware mapped for best results:
  docker compose run --rm --service-ports --device /dev/video0:/dev/video0 dev \
      python3 scripts/detect_camera.py
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional

import cv2


def which(cmd: str) -> bool:
    from shutil import which as _which

    return _which(cmd) is not None


@dataclass
class V4L2Device:
    path: str
    driver: Optional[str]
    card: Optional[str]
    can_open: bool


@dataclass
class CSIStatus:
    gst_present: bool
    can_open: bool


def list_v4l2_devices() -> List[str]:
    devs = sorted(glob.glob("/dev/video*"))
    return [d for d in devs if re.match(r"/dev/video\d+", d)]


def probe_v4l2_device(dev: str) -> V4L2Device:
    driver = None
    card = None
    if which("v4l2-ctl"):
        try:
            out = subprocess.run(
                ["v4l2-ctl", "--all", "-d", dev], capture_output=True, text=True, timeout=3
            )
            text = out.stdout
            m = re.search(r"Driver name:\s*(.+)", text)
            if m:
                driver = m.group(1).strip()
            m = re.search(r"Card type:\s*(.+)", text)
            if m:
                card = m.group(1).strip()
        except Exception:
            pass

    can_open = False
    try:
        cap = cv2.VideoCapture(dev)
        can_open = cap.isOpened()
        cap.release()
    except Exception:
        can_open = False

    return V4L2Device(path=dev, driver=driver, card=card, can_open=can_open)


def probe_csi(width: int = 1280, height: int = 720, fps: int = 30) -> CSIStatus:
    gst_present = which("gst-inspect-1.0")
    if gst_present:
        # Confirm Argus plugin exists
        try:
            r = subprocess.run(
                ["gst-inspect-1.0", "nvarguscamerasrc"],
                capture_output=True,
                text=True,
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
    return CSIStatus(gst_present=gst_present, can_open=can_open)


def classify(v4l2_devs: List[V4L2Device], csi: CSIStatus) -> str:
    has_uvc = any(
        d.can_open and (d.driver or "").lower().startswith("uvc") for d in v4l2_devs
    )
    has_any_v4l2 = any(d.can_open for d in v4l2_devs)
    has_csi = csi.gst_present and csi.can_open

    if has_csi and has_uvc:
        return "both"
    if has_uvc:
        return "usb_uvc"
    if has_csi:
        return "csi"
    if has_any_v4l2:
        return "v4l2_other"
    return "none"


def recommend(kind: str, v4l2_devs: List[V4L2Device]) -> str:
    if kind in ("usb_uvc", "v4l2_other", "both"):
        # Prefer the first openable V4L2 device
        dev = next((d.path for d in v4l2_devs if d.can_open), 
                   (v4l2_devs[0].path if v4l2_devs else "/dev/video0"))
        return f"python3 scripts/camera_stream.py --device {dev} --port 8080"
    if kind == "csi":
        return "python3 scripts/camera_stream.py --gst --width 1280 --height 720 --fps 30 --port 8080"
    return "No camera detected. Check connections and permissions."


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Detect camera type and usage recommendation")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = ap.parse_args(argv)

    v4l2_paths = list_v4l2_devices()
    v4l2_info = [probe_v4l2_device(d) for d in v4l2_paths]
    csi_info = probe_csi()
    kind = classify(v4l2_info, csi_info)
    rec = recommend(kind, v4l2_info)

    payload = {
        "v4l2_devices": [asdict(d) for d in v4l2_info],
        "csi": asdict(csi_info),
        "classification": kind,
        "recommendation": rec,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("== Camera Detection ==")
    if v4l2_info:
        for d in v4l2_info:
            driver = d.driver or "?"
            card = d.card or "?"
            status = "open" if d.can_open else "closed"
            print(f"- {d.path}: driver={driver}, card={card}, {status}")
    else:
        print("- No /dev/video* devices found")

    print("\n== CSI (Argus) ==")
    print(f"- GStreamer Argus present: {csi_info.gst_present}")
    print(f"- Can open nvarguscamerasrc: {csi_info.can_open}")

    kind_map = {
        "usb_uvc": "USB/UVC camera detected",
        "csi": "CSI (MIPI) camera detected",
        "both": "Both USB and CSI cameras detected",
        "v4l2_other": "V4L2 device detected (non-uvc)",
        "none": "No camera detected",
    }
    print(f"\n== Classification ==\n- {kind_map.get(kind, kind)}")
    print(f"\n== How to view ==\n- {rec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

