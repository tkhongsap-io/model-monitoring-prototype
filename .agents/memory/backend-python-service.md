---
name: FastAPI backend service wiring
description: How the Python backend runs in this pnpm monorepo and its native-lib/env quirks
---
- Backend venv: `.venv-backend` at repo root; install with `PIP_USER=0 pip install --no-user`.
- Long installs: background processes are killed between agent bash calls — install pinned requirements in ONE resolver pass (piecemeal installs caused numpy/scipy/shap conflicts). **Why:** shap unpinned pulls numpy>=2, breaking evidently/nannyml pins.
- lightgbm (via nannyml/flaml) needs 64-bit `libgomp.so.1`; `/nix/store` glob may match 32-bit gcc libs (ELFCLASS32 error). `backend/run.sh` probes ELF class byte to pick a 64-bit dir for LD_LIBRARY_PATH.
- Dev workflow cwd is the artifact dir, so artifact.toml dev run uses `bash ../../backend/run.sh`; prod runs from repo root.
- Demo DB is baked (seed 42) and gitignored; prod build re-bakes; run.sh resets player state to tick 0 on boot for deterministic demos.
