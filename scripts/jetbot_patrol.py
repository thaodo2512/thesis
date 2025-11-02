#!/usr/bin/env python3
"""Simple patrol routine to validate JetBot drive motors."""
import os
import sys
import time

try:
    from jetbot import Robot
except ImportError as exc:
    sys.exit(f"[jetbot-patrol] Missing jetbot SDK: {exc}")

LINE_SPEED = float(os.getenv("LINE_SPEED", "0.25"))
TURN_SPEED = float(os.getenv("TURN_SPEED", "0.2"))
STEP_SECONDS = float(os.getenv("STEP_SECONDS", "1.5"))
TURN_SECONDS = float(os.getenv("TURN_SECONDS", "0.75"))
PATROL_LAPS = int(os.getenv("PATROL_LAPS", "2"))

robot = Robot()
print(
    "[jetbot-patrol] Starting patrol:",
    f"LINE_SPEED={LINE_SPEED}",
    f"TURN_SPEED={TURN_SPEED}",
    f"STEP_SECONDS={STEP_SECONDS}",
    f"TURN_SECONDS={TURN_SECONDS}",
    f"PATROL_LAPS={PATROL_LAPS}",
)

try:
    for lap in range(1, PATROL_LAPS + 1):
        print(f"[jetbot-patrol] Lap {lap} forward")
        robot.forward(LINE_SPEED)
        time.sleep(STEP_SECONDS)

        print(f"[jetbot-patrol] Lap {lap} left turn")
        robot.left(TURN_SPEED)
        time.sleep(TURN_SECONDS)

        print(f"[jetbot-patrol] Lap {lap} forward")
        robot.forward(LINE_SPEED)
        time.sleep(STEP_SECONDS)

        print(f"[jetbot-patrol] Lap {lap} right turn")
        robot.right(TURN_SPEED)
        time.sleep(TURN_SECONDS)
finally:
    print("[jetbot-patrol] Stopping motors")
    robot.stop()
    robot.close()
