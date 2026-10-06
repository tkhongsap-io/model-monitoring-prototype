"""TraceStore implementations — sub-interface inside LLMEvalAdapter (E.1).

`SqliteTraceStore` (default) persists traces + scores to SQLite; the drill-down
Traces tab reads them back via the API. The Langfuse SDK v2 store was removed in
S2-02: SDK v4 has no trace()/score(), and the chatbot is prototype-only code.
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
