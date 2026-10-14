# Intent: batch evaluator with the core metrics (S2-05)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-14)
- **Issue:** S2-05 (#19). October scope from the 2026-10-09 change in
  `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S2-05.
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09)
- **Bands:** `changes/2026-10-08-batch-metric-profiles/core-metrics.md`, section 1.
  **RAI approved** the bands of `failure_rate`, `volume_change`, `turnaround_s` and run on
  time (reported by the project owner, 2026-10-14). Bands version: `core-2026-10-12`.

## Problem

The monitor stores each GCP run (S1-02) but does not grade it. The RAI dashboard (S2-07) and
the Sprint 2 demo (S2-08) need a grade for each run. In October the runs carry no records
(`records: []`), so the grade can use only the run body and the run history.

## Outcome

A background worker in the backend grades each stored run one time with the core metrics.
It stores the result in a new table `batch_evaluations` and sends the scores to the run's
trace in Langfuse. The `POST` request does not wait. The stored run never changes.

## Decisions (project owner, 2026-10-14)

| Decision | Reason |
|---|---|
| Run on time: S2-05 grades the **status** of each run (`completed` Green, `partial` Amber, `failed` Red). The **missing-run** check stays in S3-02. | The missing-run check needs a timer that runs when no run arrives; that is a different job. |
| A loop inside the backend, with the DB lease `batch-evaluator` (approach 1). No separate service. | The grading is cheap. One lease keeps one grader also with more instances on AWS. The code can move to a service later without a rewrite. |
| `volume_change` with fewer than 5 earlier runs is Unknown (`no_baseline`) **and stays in the rollup**: the grade is Unknown until the 6th run. | Honest: the monitor cannot yet say whether the volume is normal. Unknown is never Green. |
| Two grades: `delivery_grade` (Delivery lane) and `grade` (Reliability lane, plus Output when records come). | Core metrics rule: the delivery lane never changes the quality grade. |
| A non-empty `band_overrides` in the registry stops the backend start until the evaluator supports overrides. | An RAI-approved override is never silently ignored. |
| **uuid7 for the generated IDs of all MVP tables**, with the package `uuid-utils` (1.0.0, BSD-3-Clause, no dependencies). `batch_runs.batch_run_id` changes from uuid5 to uuid7; a migration gives the existing rows a uuid7 from `received_at`. Prototype tables do not change (S4-07 deletes them). | Time-ordered IDs sort and index well. The data is development data with low volume, so a change now is cheap. The duplicate check uses (`use_case_id`, `run_id`), not this ID. |

**New package (plan entry):** `uuid-utils>=1.0,<2`, approved by the project owner on
2026-10-14. No other new package: the Langfuse SDK came with S2-02.

## Not in scope

The missing-run timer (S3-02), records and the record metrics, the judge (S2-09, S2-10),
the quality profiles, the dashboard (S2-07), the `monitor.evaluate` span, and band
overrides.

## Success criteria

- The worker grades each new run one time; the `POST` does not wait; the stored run does
  not change.
- `batch_evaluations` stores the metrics, the bands version and the run ID. Each Unknown
  condition gives its reason.
- Langfuse shows the scores on the trace with a stable `score_id`. A Langfuse failure does
  not change the grade.
- The fast suite (with the chatbot `AICT-L02` tests), `smoke` and `langfuse-smoke` pass.
- On the test host, readiness shows `unevaluated: 0` and Langfuse shows the RTR run's
  `grade`.
