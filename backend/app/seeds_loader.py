"""Seed loader — registry_seed.json (2 deep + 13 shallow, Appendix B) + the
deterministic stub portfolio (B.8) => exactly 130 rows in SQLite.
"""
from __future__ import annotations

import json
import sys

from . import config, db

REQUIRED_DEFAULTS = {
    "source_record_id": "Unknown", "business_unit": "Unknown", "business_owner": "Unknown",
    "technical_owner": "Unknown", "monitoring_owner": "Unknown", "system_owner": "Unknown",
    "platform_or_app": "Unknown", "model_provider": "Unknown", "model_or_route": "Unknown",
    "workflow_location": "Unknown", "data_sources": "Unknown",
    "privacy_status": "Unknown", "security_status": "Unknown", "rai_status": "Unknown",
    "ai_readiness_status": "Unknown", "telemetry_status": "Unknown",
    "current_health": "Unknown", "last_reviewed": "Unknown", "next_review": "Unknown",
    "open_actions": 0,
    "quality_status": "Unknown", "safety_status": "Unknown", "reliability_status": "Unknown",
    "degradation_status": "Unknown", "feedback_status": "Unknown",
}


def build_rows(seed: int | None = None) -> list[dict]:
    seed = seed if seed is not None else config.DEMO_SEED
    with open(config.SEEDS_DIR / "registry_seed.json", encoding="utf-8") as f:
        seed_data = json.load(f)
    sys.path.insert(0, str(config.SEEDS_DIR))
    from gen_stub_portfolio import generate  # noqa: E402
    rows = []
    for r in seed_data["deep"] + seed_data["shallow"] + generate(seed):
        rows.append({**REQUIRED_DEFAULTS, **r})
    assert len(rows) == 130, f"expected 130 registry rows, got {len(rows)}"
    return rows


def seed_registry(force: bool = False, seed: int | None = None) -> int:
    existing = db.get_registry_rows()
    if existing and not force:
        return len(existing)
    rows = build_rows(seed)
    db.put_registry_rows(rows)
    return len(rows)
