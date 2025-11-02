# Repository Guidelines

## Project Structure & Module Organization
Maintain a predictable layout so research code, notebooks, and manuscript evolve together:
- `manuscript/` – LaTeX or Markdown chapters, plus `figures/` and `tables/` subfolders.
- `src/` – reusable Python modules for experiments; packages live under `src/<domain>/`.
- `experiments/` – notebooks or scripts for exploratory runs; name as `YYYYMMDD_short-topic`.
- `tests/` – mirrors `src/` for unit tests and data contracts.
- `docker/` and `docker-compose.yml` – container tooling for Jetson deployment.
- `scripts/` – operational helpers such as `test_camera.py` and `jetbot_patrol.py`.
- `data/` – keep only tiny fixtures; document larger sources in `data/README.md`.

## Build, Test, and Development Commands
Prefer reproducible containers, but keep local virtualenv parity:
- `docker compose up --build dev` – start Jupyter Lab on port 8888 for development.
- `docker compose --profile hardware run --rm camera-test` – capture a snapshot from `/dev/video0` (saves to `notebooks/camera_snapshot.jpg`).
- `docker compose --profile hardware run --rm jetbot-patrol` – drive the JetBot in a loop; tune speed via env vars.
- `python -m venv .venv && source .venv/bin/activate` – local virtual environment when debugging off-device.
- `pip install -r requirements.txt` – sync Python deps.

## Coding Style & Naming Conventions
Run `black` (line length 88) and `ruff` before committing; configure both in `pyproject.toml`. Use explicit module names (`laser_alignment.py`), snake_case functions, and descriptive notebook filenames. Keep notebooks clean with `nbstripout`. Thesis assets should be vector-first (`.svg`/`.pdf`) with slugified names.

## Testing Guidelines
Target ≥90% coverage on `src/` via `pytest --cov=src --cov-report=term-missing`. Name tests after observable behavior (`test_spectrum_filter_handles_empty_input`). Place fixtures under `tests/fixtures/` and rely on factory helpers for paths. Hardware checks belong in compose profiles (`camera-test`, `jetbot-patrol`) and should emit human-readable logs.

## Commit & Pull Request Guidelines
Follow Conventional Commits (`type(scope): summary`) so CI and changelog tooling stay consistent. Each PR should link an issue, mention datasets touched, list new compose commands or config switches, and attach rendered manuscript diffs (`make manuscript && git diff manuscript/output`). Request review, ensure CI green, and avoid merging without at least one hardware validation note when code touches the robot.

## Data & Secrets
Do not commit raw datasets, telemetry, or credentials. Store sourcing instructions in `data/README.md` and provide `.env.example` for configuration templates. Remove generated PDFs and images before committing unless they serve as golden references.
