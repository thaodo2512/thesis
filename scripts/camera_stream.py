#!/usr/bin/env python3
"""MJPEG camera streamer for Jetson/USB cameras.

- Opens a camera (UVC `/dev/video*` or CSI via GStreamer) and serves
  a live MJPEG stream over HTTP so you can view it in any browser.
  Useful in headless containers where GUI windows are unavailable.

Examples
--------
- USB camera on `/dev/video0` at 1280x720@30fps, serve on port 8080:
    python3 scripts/camera_stream.py --device /dev/video0 --width 1280 --height 720 --fps 30 --port 8080

- CSI camera (Raspberry Pi cam) via GStreamer on Jetson:
    python3 scripts/camera_stream.py --gst --width 1280 --height 720 --fps 30 --port 8080

Then open: http://<jetson-ip>:8080  (stream at /stream.mjpg)

Environment variables (optional)
--------------------------------
- VIDEO_DEVICE: overrides --device (default "/dev/video0")
- STREAM_PORT: overrides --port (default 8080)
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from http import server
from typing import Optional

import cv2


def gstreamer_pipeline(width: int, height: int, fps: int, flip: int = 0) -> str:
    """Build a GStreamer pipeline for Jetson CSI camera.

    flip: 0 (none), 2 (flip horizontal), 4 (flip vertical), etc.
    """
    return (
        "nvarguscamerasrc ! "
        f"video/x-raw(memory:NVMM), width={width}, height={height}, framerate={fps}/1 "
        "! nvvidconv "
        f"flip-method={flip} "
        "! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
    )


class FrameGrabber:
    """Background thread that grabs frames and keeps the latest JPEG bytes."""

    def __init__(
        self,
        cap: cv2.VideoCapture,
        jpeg_quality: int = 80,
        target_fps: Optional[float] = None,
    ) -> None:
        self.cap = cap
        self.jpeg_quality = int(jpeg_quality)
        self.target_interval = (1.0 / target_fps) if target_fps and target_fps > 0 else 0
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._thread = threading.Thread(target=self._loop, name="FrameGrabber", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)
        try:
            self.cap.release()
        except Exception:
            pass

    def latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def _loop(self) -> None:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        while not self._stop.is_set():
            ok, frame = self.cap.read()
            if not ok or frame is None:
                # Small backoff and try again
                time.sleep(0.01)
                continue
            ok, buf = cv2.imencode(".jpg", frame, encode_param)
            if ok:
                with self._lock:
                    self._latest_jpeg = buf.tobytes()
            if self.target_interval > 0:
                # Throttle to target FPS
                time.sleep(self.target_interval)


def build_capture(args: argparse.Namespace) -> cv2.VideoCapture:
    # Resolve device from env or CLI
    device = os.getenv("VIDEO_DEVICE", args.device)
    if args.gst:
        pipeline = gstreamer_pipeline(args.width, args.height, args.fps, args.flip)
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    else:
        # Allow numeric index like "0" or path like "/dev/video0"
        dev_spec = int(device) if device.isdigit() else device
        cap = cv2.VideoCapture(dev_spec)
        # Try to set UVC properties; not all cams honor these
        if args.width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(args.width))
        if args.height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(args.height))
        if args.fps:
            cap.set(cv2.CAP_PROP_FPS, float(args.fps))
    if not cap.isOpened():
        sys.exit(f"[camera-stream] Unable to open camera: {device} (gst={args.gst})")
    return cap


def make_http_handler(grabber: FrameGrabber):
    boundary = b"frame"

    class Handler(server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http handler sig)
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    (
                        "<html><head><title>Camera Stream</title></head><body>"
                        "<h3>Live MJPEG Stream</h3>"
                        "<img src=\"/stream.mjpg\" style=\"max-width:100%;\"/>"
                        "<p><a href=\"/snapshot.jpg\">Snapshot</a></p>"
                        "</body></html>"
                    ).encode("utf-8")
                )
                return

            if self.path == "/snapshot.jpg":
                frame = grabber.latest_jpeg()
                if not frame:
                    self.send_error(503, "No frame available yet")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
                return

            if self.path == "/stream.mjpg":
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    f"multipart/x-mixed-replace; boundary={boundary.decode()}",
                )
                self.end_headers()
                # Stream loop
                try:
                    while True:
                        frame = grabber.latest_jpeg()
                        if not frame:
                            time.sleep(0.01)
                            continue
                        self.wfile.write(b"--" + boundary + b"\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    # Client disconnected
                    return
            else:
                self.send_error(404, "Not Found")

        def log_message(self, fmt: str, *args) -> None:
            # Reduce console noise; uncomment for verbose
            # sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))
            return

    return Handler


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live MJPEG camera streamer")
    parser.add_argument("--device", default=os.getenv("VIDEO_DEVICE", "/dev/video0"))
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--flip", type=int, default=0, help="Flip method for CSI (gst) camera")
    parser.add_argument("--port", type=int, default=int(os.getenv("STREAM_PORT", 8080)))
    parser.add_argument("--quality", type=int, default=80, help="JPEG quality 1-100")
    parser.add_argument("--gst", action="store_true", help="Use CSI camera via GStreamer")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    cap = build_capture(args)
    # Use target_fps slightly lower than source to avoid backlog
    grabber = FrameGrabber(cap, jpeg_quality=args.quality, target_fps=min(args.fps, 30))
    grabber.start()

    addr = ("0.0.0.0", args.port)
    handler = make_http_handler(grabber)
    httpd = server.ThreadingHTTPServer(addr, handler)
    print(
        f"[camera-stream] Serving MJPEG on http://{addr[0]}:{addr[1]} (index/, stream.mjpg, snapshot.jpg)",
        f"device={os.getenv('VIDEO_DEVICE', args.device)} gst={args.gst} {args.width}x{args.height}@{args.fps}",
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[camera-stream] Shutting down...")
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        grabber.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
