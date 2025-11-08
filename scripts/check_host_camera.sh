#!/usr/bin/env bash
# Quick host-side diagnostics for Jetson CSI/Argus before launching containers.
set -euo pipefail

SENSOR_ID="${CSI_SENSOR_ID:-0}"
WIDTH="${CSI_WIDTH:-1280}"
HEIGHT="${CSI_HEIGHT:-720}"
FPS="${CSI_FPS:-30}"
RUN_PIPELINE=1

usage() {
    cat <<'EOF'
Usage: scripts/check_host_camera.sh [--skip-pipeline] [--sensor-id N] [--width PX] [--height PX] [--fps N]

Checks:
  1. Argus daemon status via systemctl (restart suggestion if inactive).
  2. Lists /dev/video* nodes present on the host.
  3. Verifies /tmp/argus_socket existence and ownership.
  4. (Optional) Runs a gst-launch pipeline using nvarguscamerasrc to display a live feed.

Environment overrides: CSI_SENSOR_ID, CSI_WIDTH, CSI_HEIGHT, CSI_FPS.
EOF
}

log() { printf '[check-host-camera] %s\n' "$*"; }
warn() { printf '[check-host-camera][warn] %s\n' "$*"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sensor-id)
            SENSOR_ID="$2"
            shift 2
            ;;
        --width)
            WIDTH="$2"
            shift 2
            ;;
        --height)
            HEIGHT="$2"
            shift 2
            ;;
        --fps)
            FPS="$2"
            shift 2
            ;;
        --skip-pipeline)
            RUN_PIPELINE=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            warn "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

ARGUS_SERVICE="nvargus-daemon"

log "Checking Argus daemon status (${ARGUS_SERVICE})"
if command -v systemctl >/dev/null 2>&1; then
    if ! sudo systemctl status "${ARGUS_SERVICE}" --no-pager; then
        warn "Argus daemon is inactive. Restart with: sudo systemctl restart ${ARGUS_SERVICE}"
    fi
else
    warn "systemctl not available on this host; skipping daemon status check"
fi

log "Enumerating /dev/video* devices"
shopt -s nullglob
VIDEO_NODES=(/dev/video*)
if ((${#VIDEO_NODES[@]} == 0)); then
    warn "No /dev/video* nodes found. Is the camera connected and JetPack installed?"
else
    ls -l "${VIDEO_NODES[@]}"
fi
shopt -u nullglob

ARGUS_SOCKET="/tmp/argus_socket"
log "Checking Argus socket (${ARGUS_SOCKET})"
if [[ -e "${ARGUS_SOCKET}" ]]; then
    ls -l "${ARGUS_SOCKET}"
else
    warn "${ARGUS_SOCKET} missing. Restart nvargus-daemon and try again."
fi

if (( RUN_PIPELINE )); then
    log "Running gst-launch pipeline (sensor-id=${SENSOR_ID}, ${WIDTH}x${HEIGHT}@${FPS})"
    PIPELINE=(
        gst-launch-1.0
        nvarguscamerasrc "sensor-id=${SENSOR_ID}"
        "!" "video/x-raw(memory:NVMM),width=${WIDTH},height=${HEIGHT},framerate=${FPS}/1"
        "!" nvvidconv
        "!" videoconvert
        "!" xvimagesink
    )
    printf '[check-host-camera][info] %s '\
        "${PIPELINE[@]}"
    printf '\n'
    "${PIPELINE[@]}"
else
    log "Skipping gst-launch pipeline (use --skip-pipeline to disable in future runs)."
fi

log "Checks complete. Address any warnings above before re-running Docker Compose."
