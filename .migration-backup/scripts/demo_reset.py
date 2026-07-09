#!/usr/bin/env python
"""demo_reset — the R-34 one-shot task: reseed the registry, bake DEMO-FULL at the
configured seed, and point the player at baked tick 0.

    cd backend && ./.venv/Scripts/python ../scripts/demo_reset.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config, db, seeds_loader          # noqa: E402
from app.scenario import baker                    # noqa: E402


def main() -> None:
    t0 = time.time()
    print(f"[demo_reset] seed={config.DEMO_SEED} db={config.DB_PATH}")
    n = seeds_loader.seed_registry(force=True)
    print(f"[demo_reset] registry reseeded: {n} rows")
    result = baker.bake("DEMO-FULL")
    db.put_state(scenario_id="DEMO-FULL", tick=0, playing=0, speed=1,
                 mode="baked", seed=config.DEMO_SEED)
    print(f"[demo_reset] BAKED ✓ · seed {config.DEMO_SEED} · DEMO-FULL · tick 0 "
          f"({result['total_ticks']} ticks, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
