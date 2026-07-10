"""TraceStore implementations — sub-interface inside LLMEvalAdapter (E.1).

`SqliteTraceStore` (default) persists traces + scores to SQLite; the drill-down
Traces tab reads them back via the API. `LangfuseCloudStore` mirrors the same
surface AND persists locally (the UI always reads SQLite) while pushing to
Langfuse Cloud (SDK v2 trace()/score()/flush()) — a config flip, not a code change.
"""
from __future__ import annotations

import uuid

from ... import db


class SqliteTraceStore:
    name = "sqlite"

    def __init__(self, scenario_id: str, use_case_id: str) -> None:
        self.scenario_id = scenario_id
        self.use_case_id = use_case_id
        self._tick = 0
        self._pending: list[tuple[dict, list[dict]]] = []

    def set_tick(self, tick: int) -> None:
        self._tick = tick

    def trace(self, name: str, input: str, output: str, metadata: dict) -> str:
        trace_id = uuid.uuid5(uuid.NAMESPACE_URL,
                              f"{self.scenario_id}/{self._tick}/{self.use_case_id}/{len(self._pending)}").hex
        import json
        self._pending.append((
            {"trace_id": trace_id, "scenario_id": self.scenario_id, "tick": self._tick,
             "use_case_id": self.use_case_id, "name": name, "input": input,
             "output": output, "metadata_json": json.dumps(metadata)},
            []))
        return trace_id

    def score(self, trace: str, name: str, value: float) -> None:
        for row, srows in self._pending:
            if row["trace_id"] == trace:
                srows.append({"trace_id": trace, "name": name, "value": float(value)})
                return

    def flush(self, block: bool = True) -> None:
        for row, srows in self._pending:
            db.add_trace(row, srows)
        self._pending.clear()


class LangfuseCloudStore(SqliteTraceStore):
    """Persists locally (UI reads SQLite) and pushes to Langfuse Cloud, best-effort."""
    name = "langfuse_cloud"

    def __init__(self, scenario_id: str, use_case_id: str,
                 public_key: str, secret_key: str, host: str) -> None:
        super().__init__(scenario_id, use_case_id)
        self._lf = None
        self._lf_traces: dict[str, object] = {}
        try:
            from langfuse import Langfuse
            self._lf = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        except Exception:  # noqa: BLE001 — degrade to local-only
            self._lf = None

    def trace(self, name: str, input: str, output: str, metadata: dict) -> str:
        trace_id = super().trace(name, input, output, metadata)
        if self._lf is not None:
            try:
                self._lf_traces[trace_id] = self._lf.trace(
                    name=name, input=input, output=output, metadata=metadata)
            except Exception:  # noqa: BLE001
                self._lf = None  # stop pushing after a hard failure
        return trace_id

    def score(self, trace: str, name: str, value: float) -> None:
        super().score(trace, name, value)
        lft = self._lf_traces.get(trace)
        if lft is not None:
            try:
                lft.score(name=name, value=float(value))
            except Exception:  # noqa: BLE001
                pass

    def flush(self, block: bool = True) -> None:
        super().flush()
        self._lf_traces.clear()
        # block=True (baked path): force a synchronous send so nothing is lost. block=False
        # (live path): queue only — the Langfuse SDK's background thread delivers within ~1s,
        # so a live tick isn't stalled ~20s waiting on the round-trip to the cloud.
        if self._lf is not None and block:
            try:
                self._lf.flush()
            except Exception:  # noqa: BLE001
                pass
