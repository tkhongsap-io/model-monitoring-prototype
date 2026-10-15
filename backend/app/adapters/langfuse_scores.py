"""Scores of one batch evaluation on the run's trace in self-hosted Langfuse (S2-05).

`score_id` is stable (uuid5 of the evaluation ID and the score name), so a retry makes no
duplicate. The synchronous API call raises on failure; the SDK's `create_score` queues and
never raises, so it is not used. No record text and no key is sent or logged.
Each run's scores go to the project of its use case (S2-03b); without its keys, to `unrouted`.
"""
from __future__ import annotations

import json
import uuid

from .. import config

SCORE_NAMESPACE = uuid.UUID("6f1d3f5e-2b8a-4c1e-9d3a-5b7c2e4f8a10")
NUMERIC_SCORES = ("failure_rate", "volume_change", "turnaround_s")


def score_id(evaluation_id: str, name: str) -> str:
    return str(uuid.uuid5(SCORE_NAMESPACE, f"{evaluation_id}:{name}"))


def _comment(bands_version: str, metrics: list[dict]) -> str:
    unknown = [f"{m['name']}={m['reason']}" for m in metrics if m["health"] == "Unknown"]
    return f"bands {bands_version}; unknown: {', '.join(unknown) or 'none'}"


def scores_for(evaluation: dict) -> list[dict]:
    metrics = json.loads(evaluation["metrics"])
    bands = evaluation["bands_version"]
    delivery = [m for m in metrics if m["lane"] == "Delivery"]
    rollup = [m for m in metrics if m["lane"] != "Delivery" and m["in_rollup"]]
    out = [
        {"name": "grade", "value": evaluation["grade"], "data_type": "CATEGORICAL",
         "comment": _comment(bands, rollup)},
        {"name": "delivery_grade", "value": evaluation["delivery_grade"],
         "data_type": "CATEGORICAL", "comment": _comment(bands, delivery)},
    ]
    for m in metrics:
        if m["name"] in NUMERIC_SCORES and m["value"] is not None:
            out.append({"name": m["name"], "value": m["value"], "data_type": "NUMERIC",
                        "comment": m["health"]})
    return [{"id": score_id(evaluation["evaluation_id"], s["name"]), **s} for s in out]


class LangfuseScoreSender:
    """Sends the scores of one evaluation to the Langfuse project of its use case (S2-03b)."""

    def __init__(self, client_for) -> None:
        self._client_for = client_for

    def send(self, evaluation: dict) -> None:
        from langfuse.api import ScoreDataType
        client = self._client_for(evaluation.get("use_case_id"))
        if client is None:
            raise LookupError("no Langfuse project keys for this use case")
        for score in scores_for(evaluation):
            client.api.scores.create(
                name=score["name"], value=score["value"], id=score["id"],
                trace_id=evaluation["trace_id"], data_type=ScoreDataType(score["data_type"]),
                comment=score["comment"])


def make_sender() -> LangfuseScoreSender | None:
    host = config.EVALUATOR_LANGFUSE_HOST
    keys = config.langfuse_project_keys()
    if not host or not keys:
        return None
    from ..langfuse_projects import keys_for
    clients: dict[str, object] = {}

    def client_for(use_case_id: str | None):
        found = keys_for(keys, use_case_id)
        if found is None:
            return None
        project, (public_key, secret_key) = found
        if project not in clients:
            import langfuse
            clients[project] = langfuse.Langfuse(public_key=public_key, secret_key=secret_key,
                                                 host=host, tracing_enabled=False, timeout=10)
        return clients[project]

    return LangfuseScoreSender(client_for)
