"""Container-friendly bake entrypoint (twin of scripts/demo_reset.py).

Same three steps as demo_reset — reseed the 130-row registry, bake DEMO-FULL at
the configured seed, point the player at baked tick 0 — but WITHOUT the sys.path
hack: this file is meant to be run from the backend dir (WORKDIR /app in Docker)
where `app` is already importable. Used at image-build time so the container ships
demo-ready (the ~90s seed-42 bake runs once, in the builder, not at request time).

    cd backend && python bake.py
"""
from __future__ import annotations

import time

from app import config, db, seeds_loader
from app.scenario import baker


def main() -> None:
    t0 = time.time()
    print(f"[bake] seed={config.DEMO_SEED} db={config.DB_PATH}")
    n = seeds_loader.seed_registry(force=True)
    print(f"[bake] registry reseeded: {n} rows")
    result = baker.bake("DEMO-FULL")
    db.put_state(scenario_id="DEMO-FULL", tick=0, playing=0, speed=1,
                 mode="baked", seed=config.DEMO_SEED)
    print(f"[bake] BAKED OK · seed {config.DEMO_SEED} · DEMO-FULL · tick 0 "
          f"({result['total_ticks']} ticks, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
