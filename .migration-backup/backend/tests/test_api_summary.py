"""Summary API assertions for the At A Glance portfolio map."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import config, db, seeds_loader
from app.api.routes import router
from app.scenario.player import reset_player


def test_summary_portfolio_map_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "summary.db")
    monkeypatch.setattr(config, "ARTIFACTS_DIR", tmp_path / "artifacts")
    db.reset_engine()
    reset_player()

    try:
        seeds_loader.seed_registry(force=True, seed=42)
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            payload = client.get("/api/summary").json()

        assert payload["use_case_count"] == 130
        assert payload["status_counts"] == {
            "production": 38,
            "in_development": 36,
            "requirements_not_started": 40,
            "paused": 3,
            "retired_cancelled": 13,
        }
        assert payload["high_risk_missing_approval"] == 4
        assert payload["missing_risk_assessment"] == 12
        assert payload["pilot_count"] == 15

        rows = payload["portfolio_map"]
        assert len(rows) == 130
        assert [r["registry_id"] for r in rows] == [f"AICT-P{i:02d}" for i in range(1, 100)] + [
            f"AICT-P{i}" for i in range(100, 131)
        ]
        assert payload["readiness_counts"] == {
            "deep_simulated": 2,
            "pilot_register_only": 13,
            "not_instrumented": 115,
        }
        assert [r["monitoring_readiness"] for r in rows[:2]] == ["deep_simulated", "deep_simulated"]
        assert {r["monitoring_readiness"] for r in rows[2:15]} == {"pilot_register_only"}
        assert {r["monitoring_readiness"] for r in rows[15:]} == {"not_instrumented"}
    finally:
        reset_player()
        db.reset_engine()
