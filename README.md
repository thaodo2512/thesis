# JetBot Policy-Learning Path Planner

## Overview
This project targets NVIDIA Jetson Nano-powered JetBot platforms that need to navigate from point **A** to point **B** while avoiding dynamic obstacles. The long-term goal is to evaluate policy-learning approaches (reinforcement learning and imitation learning) that can adapt online to new layouts inside labs, classrooms, or workshops.

## Hardware & Software Stack
- **Robot**: NVIDIA JetBot with stereo camera and wheel encoders.
- **Compute**: Jetson Nano 4GB module, Ubuntu 18.04 / JetPack 4.x.
- **Core Libraries**: `torch` for policy networks, `gymnasium` for simulation, `isaac-sim` or `pybullet` for domain randomisation, `jetbot` SDK for low-level control.
- **Dev Environment**: Remote container or SSH workflow from a development laptop.

## Project Objectives
1. Build a reproducible simulation-to-real pipeline for training navigation policies.
2. Benchmark candidate policy-learning algorithms (PPO, SAC, behavior cloning) using consistent metrics (episode reward, collision rate, traversal time).
3. Deploy the best-performing policy to the JetBot and collect closed-loop telemetry for continual improvement.

## Getting Started
1. Flash the Jetson Nano with the latest JetPack image and enable swap (at least 4GB).
2. Clone this repository onto the Jetson (`git clone <repo> && cd thesis`).
3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Verify JetBot drivers with `python scripts/check_hardware.py` (to be implemented).

## Docker Compose Usage
- Build and launch Jupyter Lab for development:
  ```bash
  docker compose up --build dev
  ```
  Then open `http://<jetson-ip>:8888`.
- Capture a camera snapshot (requires `/dev/video0`):
  ```bash
  docker compose --profile hardware run --rm camera-test
  ```
  Snapshot saved to `notebooks/camera_snapshot.jpg`.
- Patrol test to drive the JetBot in a simple loop:
  ```bash
  docker compose --profile hardware run --rm jetbot-patrol
  ```
  Override speed and duration with env vars (`LINE_SPEED`, `TURN_SPEED`, `STEP_SECONDS`, `TURN_SECONDS`, `PATROL_LAPS`).

## Roadmap
- [ ] Draft requirements and baseline environments inside `sim/`.
- [ ] Implement data logging (`logs/`) and replay buffers (`src/replay/`).
- [ ] Create behaviour cloning baseline from teleoperation recordings.
- [ ] Train PPO policy in simulation and transfer to hardware tests.
- [ ] Integrate telemetry dashboard for real-time monitoring.

Contributions welcome—see `AGENTS.md` for contributor workflow and standards.
