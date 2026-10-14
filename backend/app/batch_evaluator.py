"""Batch evaluator (S2-05): grades each stored run one time, then sends the scores.

An asyncio task of the backend lifespan. Each cycle runs in a thread and needs the DB lease
`batch-evaluator`, so one instance grades also when more instances run. A cycle error is
logged by class and message and the next cycle runs normally; the API never stops. The
POST request never waits for this worker.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable

from . import config, db, ids, registry
from .adapters import langfuse_scores
from .engines.batch_grading import BANDS_VERSION, grade_run, select_baseline

log = logging.getLogger(__name__)

LEASE_NAME = "batch-evaluator"
MAX_LANGFUSE_ATTEMPTS = 20
BATCH = 50
_DEFAULT = object()
_current: "Evaluator | None" = None


class Evaluator:
    def __init__(self, sender=_DEFAULT, now: Callable[[], float] = time.time) -> None:
        self.sender = langfuse_scores.make_sender() if sender is _DEFAULT else sender
        self.now = now
        self.owner_id = f"{socket.gethostname()}:{os.getpid()}:{ids.new_id()[-12:]}"
        self.last_cycle_at: float | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    # ---------------------------------------------------------------- one cycle
    def run_cycle(self) -> dict:
        ttl = 3 * config.BATCH_EVALUATOR_INTERVAL_S
        if not db.acquire_live_lease(LEASE_NAME, self.owner_id, ttl):
            return {"lease": False, "graded": 0, "sent": 0}
        graded = 0
        for run in db.runs_without_evaluation(BANDS_VERSION, BATCH):
            try:
                graded += self._grade(run)
            except Exception as exc:  # noqa: BLE001 — one run never stops the others
                log.warning("batch evaluation failed", extra={
                    "use_case_id": run.get("use_case_id"), "run_id": run.get("run_id"),
                    "error": type(exc).__name__})
        sent = self._send_scores()
        self.last_cycle_at = self.now()
        return {"lease": True, "graded": graded, "sent": sent}

    def _grade(self, run: dict) -> int:
        body = json.loads(run["payload"])
        history = db.batch_run_history(run["use_case_id"])
        baseline = select_baseline(history, run["batch_run_id"], run["completed_at"])
        use_case = registry.current().get(run["use_case_id"])
        limit = use_case.turnaround_limit_s if use_case else None
        grade = grade_run(body, [b["request_count"] for b in baseline], limit)
        row = {
            "evaluation_id": ids.new_id(), "batch_run_id": run["batch_run_id"],
            "use_case_id": run["use_case_id"], "run_id": run["run_id"],
            "trace_id": run["trace_id"], "bands_version": grade.bands_version,
            "metrics": json.dumps([asdict(m) for m in grade.metrics]),
            "delivery_grade": grade.delivery_grade, "grade": grade.grade,
            "baseline_run_ids": json.dumps([b["batch_run_id"] for b in baseline]),
            "evaluated_at": self.now(),
            "langfuse_status": "pending" if self.sender is not None else "skipped",
            "langfuse_attempts": 0, "langfuse_error": None,
        }
        if not db.put_batch_evaluation(row):
            return 0
        log.info("batch run graded", extra={
            "use_case_id": run["use_case_id"], "run_id": run["run_id"],
            "trace_id": run["trace_id"], "grade": grade.grade,
            "delivery_grade": grade.delivery_grade})
        return 1

    def _send_scores(self) -> int:
        if self.sender is None:
            return 0
        sent = 0
        for evaluation in db.evaluations_for_langfuse(BATCH):
            try:
                self.sender.send(evaluation)
            except Exception as exc:  # noqa: BLE001 — the grade is stored; retry later
                attempts = int(evaluation["langfuse_attempts"]) + 1
                status = "failed" if attempts >= MAX_LANGFUSE_ATTEMPTS else "pending"
                db.set_langfuse_result(evaluation["evaluation_id"], status, type(exc).__name__)
                continue
            db.set_langfuse_result(evaluation["evaluation_id"], "sent", None)
            sent += 1
        return sent

    # ---------------------------------------------------------------- the loop
    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.run_cycle)
            except Exception as exc:  # noqa: BLE001 — log and try again next cycle
                log.warning("batch evaluator cycle failed", extra={"error": type(exc).__name__})
            try:
                await asyncio.wait_for(self._stop.wait(), config.BATCH_EVALUATOR_INTERVAL_S)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        self._stop = asyncio.Event()
        self._task = asyncio.get_running_loop().create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, 10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        try:
            await asyncio.to_thread(db.release_live_lease, LEASE_NAME, self.owner_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("batch evaluator lease release failed",
                        extra={"error": type(exc).__name__})


def start() -> Evaluator:
    global _current
    _current = Evaluator()
    _current.start()
    return _current


async def stop() -> None:
    global _current
    if _current is not None:
        await _current.stop()
    _current = None


def current() -> Evaluator | None:
    return _current


def status() -> dict:
    """The readiness object. No key, no body; counts are None when the DB fails."""
    worker = _current
    last = worker.last_cycle_at if worker else None
    try:
        counts = db.evaluator_counts(BANDS_VERSION)
    except Exception:  # noqa: BLE001 — readiness reports the database separately
        counts = {"unevaluated": None, "langfuse_pending": None}
    return {
        "enabled": bool(config.BATCH_EVALUATOR_ENABLED),
        "last_cycle_at": (datetime.fromtimestamp(last, timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ") if last else None),
        **counts,
    }
