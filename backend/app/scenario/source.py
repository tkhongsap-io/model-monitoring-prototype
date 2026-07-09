"""ScenarioSource — NON-engine input interface (E.1); loads simulation.yaml (§A.4).

Standalone S1–S5 are served as views into the single DEMO-FULL bake: the master
timeline was composed from them, so their tick states are identical and the
declared start-snapshots come free as tick pointers (scenario_ranges in the yaml).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .. import config


@dataclass
class ScenarioScript:
    scenario_id: str
    name: str
    ticks: int
    churn_alpha: list[float]
    llm_halluc: list[int]
    events: list[dict] = field(default_factory=list)
    range_in_master: tuple[int, int] = (0, 19)


class YamlScenarioSource:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config.SCENARIOS_YAML
        with open(self.path, encoding="utf-8") as f:
            self.cfg: dict[str, Any] = yaml.safe_load(f)

    @property
    def sim(self) -> dict:
        return self.cfg["sim"]

    @property
    def churn(self) -> dict:
        return self.cfg["churn"]

    @property
    def bands(self) -> dict:
        return self.cfg["bands"]

    @property
    def snapshots(self) -> dict[str, int]:
        return dict(self.cfg.get("snapshots", {}))

    def scenario_ids(self) -> list[str]:
        return list(self.cfg["scenarios"].keys())

    def load(self, scenario_id: str) -> ScenarioScript:
        s = self.cfg["scenarios"].get(scenario_id)
        if s is None:
            raise KeyError(f"unknown scenario: {scenario_id}")
        rng = self.cfg.get("scenario_ranges", {}).get(scenario_id, [0, int(s["ticks"]) - 1])
        return ScenarioScript(
            scenario_id=scenario_id, name=s.get("name", scenario_id),
            ticks=int(s["ticks"]), churn_alpha=list(s.get("churn_alpha", [])),
            llm_halluc=list(s.get("llm_halluc", [])), events=list(s.get("events", [])),
            range_in_master=(int(rng[0]), int(rng[1])),
        )
