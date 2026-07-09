"""Scenario player — tick pointer over baked ticks (§A.1.2), server-side state,
session-local overlay, and an in-process event broadcaster for SSE.

Standalone scenarios are views into the DEMO-FULL bake (source.py): the player maps
a local tick to the master tick via the scenario's range. Advancing/jumping/reset
are DB reads / pointer swaps — never a live engine run in demo mode.
"""
from __future__ import annotations

import asyncio
import copy
import time

from .. import config, db
from .baker import MASTER
from .source import YamlScenarioSource


class EventBroker:
    """Fan-out of scenario events to SSE subscribers."""

    def __init__(self) -> None:
        self._subs: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subs.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subs:
            self._subs.remove(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


class Player:
    def __init__(self) -> None:
        self.src = YamlScenarioSource()
        self.broker = EventBroker()
        self.overlay: dict[str, dict] = {}          # session-local action edits (§A.1.2)
        self._play_task: asyncio.Task | None = None
        st = db.get_state()
        self.scenario_id = (st or {}).get("scenario_id") or config.DEFAULT_SCENARIO
        if self.scenario_id not in self.src.scenario_ids():
            self.scenario_id = "DEMO-FULL"
        self.tick = int((st or {}).get("tick") or 0)
        self.playing = False
        self.speed = int((st or {}).get("speed") or 1)
        self.seed = int((st or {}).get("seed") or config.DEMO_SEED)

    # ------------------------------------------------------------- mapping

    def _range(self) -> tuple[int, int]:
        return self.src.load(self.scenario_id).range_in_master

    def total_ticks(self) -> int:
        lo, hi = self._range()
        return hi - lo + 1

    def master_tick(self, local_tick: int | None = None) -> int:
        lo, _ = self._range()
        return lo + (self.tick if local_tick is None else local_tick)

    def payload(self, local_tick: int | None = None) -> dict | None:
        p = db.get_baked_tick(MASTER, self.master_tick(local_tick))
        if p is None:
            return None
        p = copy.deepcopy(p)
        p["local_tick"] = self.tick if local_tick is None else local_tick
        p["scenario_id"] = self.scenario_id
        p["total_ticks"] = self.total_ticks()
        # apply session-local overlay to actions (discarded on jump/reset)
        if self.overlay:
            for a in p.get("actions", []):
                patch = self.overlay.get(a["action_id"])
                if patch:
                    a.update(patch)
        return p

    def is_baked(self) -> bool:
        return db.baked_tick_count(MASTER) > 0

    # ------------------------------------------------------------- state + persistence

    def state(self) -> dict:
        p = self.payload()
        return {
            "scenario_id": self.scenario_id, "tick": self.tick,
            "total_ticks": self.total_ticks(), "playing": self.playing,
            "speed": self.speed, "mode": "baked", "seed": self.seed,
            "baked": self.is_baked(),
            "date": (p or {}).get("date"),
            "events_this_tick": (p or {}).get("events", []),
            "summary": (p or {}).get("summary", {}),
            "snapshots": self.src.snapshots,
        }

    def _persist(self) -> None:
        db.put_state(scenario_id=self.scenario_id, tick=self.tick,
                     playing=1 if self.playing else 0, speed=self.speed,
                     mode="baked", seed=self.seed)

    def _emit_state(self, extra: dict | None = None) -> None:
        self.broker.publish({"event": "scenario_state", "data": {**self.state(), **(extra or {})}})

    # ------------------------------------------------------------- controls

    def load(self, scenario_id: str) -> dict:
        if scenario_id not in self.src.scenario_ids():
            raise KeyError(scenario_id)
        self.pause()
        self.scenario_id = scenario_id
        self.tick = 0
        self.overlay.clear()
        self._persist()
        self._emit_state()
        return {"scenario_id": scenario_id, "tick": 0,
                "total_ticks": self.total_ticks(), "mode": "baked"}

    def step(self) -> dict:
        t0 = time.perf_counter()
        if self.tick < self.total_ticks() - 1:
            self.tick += 1
        self._persist()
        p = self.payload() or {}
        for ev in p.get("events", []):
            self.broker.publish({"event": ev.get("type", "tick_event"),
                                 "data": {**ev, "tick": self.tick}})
        self._emit_state({"step_ms": round((time.perf_counter() - t0) * 1000, 1)})
        return {"tick": self.tick, "events_this_tick": p.get("events", []),
                "summary": p.get("summary", {})}

    def jump(self, tick: int) -> dict:
        self.tick = max(0, min(int(tick), self.total_ticks() - 1))
        self.overlay.clear()  # discards session overlay (§A.1.2)
        self._persist()
        self._emit_state()
        return {"tick": self.tick}

    def reset(self) -> dict:
        t0 = time.perf_counter()
        self.pause()
        self.tick = 0
        self.overlay.clear()
        self._persist()
        self._emit_state({"reset_ms": round((time.perf_counter() - t0) * 1000, 1)})
        return {"scenario_id": self.scenario_id, "tick": 0}

    def set_speed(self, multiplier: int) -> dict:
        if multiplier not in (1, 2, 4):
            raise ValueError("multiplier must be 1, 2 or 4")
        self.speed = multiplier
        self._persist()
        self._emit_state()
        return {"speed": self.speed, "multiplier": self.speed}

    async def _play_loop(self) -> None:
        base = float(self.src.sim.get("play_seconds_per_tick", 2.0))
        try:
            while self.playing and self.tick < self.total_ticks() - 1:
                await asyncio.sleep(base / self.speed)
                if not self.playing:
                    break
                self.step()
            self.playing = False
            self._persist()
            self._emit_state()
        except asyncio.CancelledError:  # pragma: no cover
            pass

    def play(self) -> dict:
        """Must be called from the event loop (async route) — the play loop is an
        asyncio task on the server's main loop."""
        if not self.playing:
            self.playing = True
            self._persist()
            loop = asyncio.get_running_loop()
            self._play_task = loop.create_task(self._play_loop())
            self._emit_state()
        return {"playing": True, "speed": self.speed}

    def pause(self) -> dict:
        self.playing = False
        if self._play_task:
            self._play_task.cancel()
            self._play_task = None
        self._persist()
        return {"playing": False, "tick": self.tick}

    # ------------------------------------------------------------- overlay

    def patch_action(self, action_id: str, patch: dict) -> dict | None:
        p = self.payload()
        if not p:
            return None
        for a in p.get("actions", []):
            if a["action_id"] == action_id:
                clean = {k: v for k, v in patch.items()
                         if k in ("status", "owner", "due_date", "evidence_link") and v is not None}
                self.overlay[action_id] = {**self.overlay.get(action_id, {}), **clean}
                a.update(clean)
                return a
        return None


_player: Player | None = None


def player() -> Player:
    global _player
    if _player is None:
        _player = Player()
    return _player


def reset_player() -> None:
    global _player
    _player = None
