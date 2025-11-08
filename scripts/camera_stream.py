#!/usr/bin/env python3
"""MJPEG camera streamer for Jetson CSI cameras (nvarguscamerasrc).

- Opens the CSI camera via GStreamer (Argus) and serves a live MJPEG
  stream over HTTP so you can view it in any browser.
  Useful in headless containers where GUI windows are unavailable.

Examples
--------
- Example: 1280x720@30fps, serve on port 8080:
    python3 scripts/camera_stream.py --width 1280 --height 720 --fps 30 --port 8080

Then open: http://<jetson-ip>:8080  (stream at /stream.mjpg)

Environment variables (optional)
--------------------------------
- STREAM_PORT: overrides --port (default 8080)
"""

import argparse
import os
import sys
import threading
import time
from http import server
from pathlib import Path
from typing import Optional, List
import socketserver

import cv2


def gstreamer_pipeline(width, height, fps, flip=0, sensor_id=0, sensor_mode=None):
    """Build a GStreamer pipeline for Jetson CSI camera.

    flip: 0 (none), 2 (flip horizontal), 4 (flip vertical), etc.
    """
    mode = f" sensor-mode={sensor_mode}" if sensor_mode is not None else ""
    return (
        f"nvarguscamerasrc sensor-id={sensor_id}{mode} ! "
        f"video/x-raw(memory:NVMM), width={width}, height={height}, framerate={fps}/1 "
        f"! nvvidconv flip-method={flip} ! video/x-raw, format=RGBA ! "
        "appsink drop=true max-buffers=1 sync=false"
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
            # Convert RGBA to BGR before JPEG encoding
            if frame is not None and frame.ndim == 3 and frame.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:
                frame_bgr = frame
            ok, buf = cv2.imencode(".jpg", frame_bgr, encode_param)
            if ok:
                with self._lock:
                    self._latest_jpeg = buf.tobytes()
            if self.target_interval > 0:
                # Throttle to target FPS
                time.sleep(self.target_interval)


def _describe_path(prefix: str, path: Path) -> None:
    if path.exists():
        try:
            stat = path.stat()
            print(
                f"[camera-stream][debug] {prefix}: exists owner={stat.st_uid}:{stat.st_gid} "
                f"mode={oct(stat.st_mode & 0o777)}"
            )
        except OSError as exc:
            print(f"[camera-stream][debug] {prefix}: exists but stat failed ({exc})")
    else:
        print(f"[camera-stream][debug] {prefix}: MISSING")


def log_environment(args, pipeline: str) -> None:
    print(f"[camera-stream][debug] Attempting pipeline: {pipeline}")
    _describe_path("Argus socket /tmp/argus_socket", Path("/tmp/argus_socket"))
    _describe_path(f"CSI device /dev/video{args.sensor_id}", Path(f"/dev/video{args.sensor_id}"))
    video_nodes = sorted(Path("/dev").glob("video*"))
    print(
        "[camera-stream][debug] Video nodes visible: "
        + (", ".join(node.name for node in video_nodes) if video_nodes else "<none>")
    )
    print(
        "[camera-stream][debug] Env CSI_WIDTH/HEIGHT/FPS/ID/MODE="
        f"{args.width}/{args.height}/{args.fps}/{args.sensor_id}/{args.sensor_mode}"
    )


def build_capture(args):
    pipeline = gstreamer_pipeline(
        args.width, args.height, args.fps, args.flip, args.sensor_id, args.sensor_mode
    )
    log_environment(args, pipeline)
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        sys.exit(
            "[camera-stream] Unable to open CSI camera via nvarguscamerasrc. "
            "See debug output above for Argus/device status."
        )
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


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Live MJPEG camera streamer (CSI)")
    # Allow overriding via environment variables for compose usage
    def _env_int(name, default):
        try:
            return int(os.getenv(name, default))
        except Exception:
            return int(default)

    parser.add_argument("--width", type=int, default=_env_int("CSI_WIDTH", 1280))
    parser.add_argument("--height", type=int, default=_env_int("CSI_HEIGHT", 720))
    parser.add_argument("--fps", type=int, default=_env_int("CSI_FPS", 30))
    parser.add_argument(
        "--flip",
        type=int,
        default=_env_int("CSI_FLIP", 0),
        help="Flip method for CSI camera (0..7)",
    )
    parser.add_argument("--sensor-id", type=int, default=int(os.getenv("CSI_SENSOR_ID", 0)))
    parser.add_argument(
        "--sensor-mode",
        type=int,
        default=(int(os.getenv("CSI_SENSOR_MODE")) if os.getenv("CSI_SENSOR_MODE") else None),
        help="Argus sensor mode (optional)",
    )
    parser.add_argument("--port", type=int, default=int(os.getenv("STREAM_PORT", 8080)))
    parser.add_argument("--quality", type=int, default=80, help="JPEG quality 1-100")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    cap = build_capture(args)
    # Use target_fps slightly lower than source to avoid backlog
    grabber = FrameGrabber(cap, jpeg_quality=args.quality, target_fps=min(args.fps, 30))
    grabber.start()

    addr = ("0.0.0.0", args.port)
    handler = make_http_handler(grabber)
    # Python <3.7 fallback for ThreadingHTTPServer
    try:
        HTTPServer = server.ThreadingHTTPServer  # type: ignore[attr-defined]
    except AttributeError:
        class ThreadingHTTPServer(socketserver.ThreadingMixIn, server.HTTPServer):
            daemon_threads = True

        HTTPServer = ThreadingHTTPServer
    httpd = HTTPServer(addr, handler)
    print(
        f"[camera-stream] Serving MJPEG on http://{addr[0]}:{addr[1]} (index/, stream.mjpg, snapshot.jpg)"
        f" {args.width}x{args.height}@{args.fps} via CSI (nvarguscamerasrc)",
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
