"""SQLite persistence (SQLAlchemy Core, portable SQL only — ADR-1).

Tables: registry (seed rows) · baked_ticks (full per-tick state snapshots, JSON) ·
traces + scores (Langfuse-stub trace store) · artifact_map (artifact_id → file) ·
scenario_state (the player pointer) · bake_manifest (determinism manifest, §A.6).

Bake-mode design: each baked tick stores the COMPLETE state at that tick (signals,
lane healths, actions, alerts, events, summary) so advancing/jumping is one SELECT.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import (
    Column, Float, Integer, MetaData, String, Table, Text, create_engine, delete, insert, select, update,
)

from . import config

metadata = MetaData()

registry = Table(
    "registry", metadata,
    Column("registry_id", String, primary_key=True),
    Column("payload", Text, nullable=False),  # full Appendix-B row as JSON
)

baked_ticks = Table(
    "baked_ticks", metadata,
    Column("scenario_id", String, primary_key=True),
    Column("tick", Integer, primary_key=True),
    Column("payload", Text, nullable=False),  # complete tick state as JSON
)

traces = Table(
    "traces", metadata,
    Column("trace_id", String, primary_key=True),
    Column("scenario_id", String),
    Column("tick", Integer),
    Column("use_case_id", String),
    Column("name", String),
    Column("input", Text),
    Column("output", Text),
    Column("metadata_json", Text),
)

scores = Table(
    "scores", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trace_id", String),
    Column("name", String),
    Column("value", Float),
)

artifact_map = Table(
    "artifact_map", metadata,
    Column("artifact_id", String, primary_key=True),
    Column("scenario_id", String),
    Column("tick", Integer),
    Column("kind", String),        # evidently_html | lime_html | shap_png
    Column("filename", String),    # relative to ARTIFACTS_DIR
    Column("content_type", String),
)

scenario_state = Table(
    "scenario_state", metadata,
    Column("id", Integer, primary_key=True),  # single row, id=1
    Column("scenario_id", String),
    Column("tick", Integer),
    Column("playing", Integer),
    Column("speed", Integer),
    Column("mode", String),
    Column("seed", Integer),
)

bake_manifest = Table(
    "bake_manifest", metadata,
    Column("scenario_id", String, primary_key=True),
    Column("manifest", Text),
)

_engine = None


def engine():
    global _engine
    if _engine is None:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{config.DB_PATH}", future=True)
        metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    """Testing hook: drop the cached engine (e.g., after swapping DB path)."""
    global _engine
    _engine = None


# ---------------------------------------------------------------- helpers

def put_registry_rows(rows: list[dict]) -> None:
    with engine().begin() as cx:
        cx.execute(delete(registry))
        cx.execute(insert(registry), [
            {"registry_id": r["registry_id"], "payload": json.dumps(r)} for r in rows
        ])


def get_registry_rows() -> list[dict]:
    with engine().begin() as cx:
        rows = cx.execute(select(registry.c.payload).order_by(registry.c.registry_id)).fetchall()
    return [json.loads(r[0]) for r in rows]


def put_baked_tick(scenario_id: str, tick: int, payload: dict) -> None:
    with engine().begin() as cx:
        cx.execute(delete(baked_ticks).where(
            (baked_ticks.c.scenario_id == scenario_id) & (baked_ticks.c.tick == tick)))
        cx.execute(insert(baked_ticks), {
            "scenario_id": scenario_id, "tick": tick, "payload": json.dumps(payload)})


def get_baked_tick(scenario_id: str, tick: int) -> dict | None:
    with engine().begin() as cx:
        row = cx.execute(select(baked_ticks.c.payload).where(
            (baked_ticks.c.scenario_id == scenario_id) & (baked_ticks.c.tick == tick))).fetchone()
    return json.loads(row[0]) if row else None


def baked_tick_count(scenario_id: str) -> int:
    with engine().begin() as cx:
        rows = cx.execute(select(baked_ticks.c.tick).where(
            baked_ticks.c.scenario_id == scenario_id)).fetchall()
    return len(rows)


def clear_bake(scenario_id: str) -> None:
    with engine().begin() as cx:
        cx.execute(delete(baked_ticks).where(baked_ticks.c.scenario_id == scenario_id))
        cx.execute(delete(traces).where(traces.c.scenario_id == scenario_id))
        cx.execute(delete(artifact_map).where(artifact_map.c.scenario_id == scenario_id))
        cx.execute(delete(bake_manifest).where(bake_manifest.c.scenario_id == scenario_id))


def add_trace(row: dict, score_rows: list[dict]) -> None:
    with engine().begin() as cx:
        cx.execute(insert(traces), row)
        if score_rows:
            cx.execute(insert(scores), score_rows)


def get_traces(scenario_id: str, tick: int, use_case_id: str, limit: int = 40) -> list[dict]:
    with engine().begin() as cx:
        rows = cx.execute(
            select(traces).where(
                (traces.c.scenario_id == scenario_id) & (traces.c.tick == tick)
                & (traces.c.use_case_id == use_case_id)).limit(limit)).mappings().all()
        out = []
        for r in rows:
            srows = cx.execute(select(scores.c.name, scores.c.value).where(
                scores.c.trace_id == r["trace_id"])).fetchall()
            out.append({
                "trace_id": r["trace_id"], "name": r["name"], "input": r["input"],
                "output": r["output"], "metadata": json.loads(r["metadata_json"] or "{}"),
                "scores": {n: v for n, v in srows},
            })
    return out


def put_artifact(artifact_id: str, scenario_id: str, tick: int, kind: str,
                 filename: str, content_type: str) -> None:
    with engine().begin() as cx:
        cx.execute(delete(artifact_map).where(artifact_map.c.artifact_id == artifact_id))
        cx.execute(insert(artifact_map), {
            "artifact_id": artifact_id, "scenario_id": scenario_id, "tick": tick,
            "kind": kind, "filename": filename, "content_type": content_type})


def get_artifact(artifact_id: str) -> dict | None:
    with engine().begin() as cx:
        row = cx.execute(select(artifact_map).where(
            artifact_map.c.artifact_id == artifact_id)).mappings().fetchone()
    return dict(row) if row else None


def get_state() -> dict | None:
    with engine().begin() as cx:
        row = cx.execute(select(scenario_state).where(scenario_state.c.id == 1)).mappings().fetchone()
    return dict(row) if row else None


def put_state(**kw: Any) -> None:
    with engine().begin() as cx:
        if cx.execute(select(scenario_state.c.id).where(scenario_state.c.id == 1)).fetchone():
            cx.execute(update(scenario_state).where(scenario_state.c.id == 1).values(**kw))
        else:
            cx.execute(insert(scenario_state), {"id": 1, **kw})


def put_manifest(scenario_id: str, manifest: dict) -> None:
    with engine().begin() as cx:
        cx.execute(delete(bake_manifest).where(bake_manifest.c.scenario_id == scenario_id))
        cx.execute(insert(bake_manifest), {"scenario_id": scenario_id, "manifest": json.dumps(manifest)})


def get_manifest(scenario_id: str) -> dict | None:
    with engine().begin() as cx:
        row = cx.execute(select(bake_manifest.c.manifest).where(
            bake_manifest.c.scenario_id == scenario_id)).fetchone()
    return json.loads(row[0]) if row else None
