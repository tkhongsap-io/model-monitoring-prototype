# Diagrams

Numbered pictures of the system, as it stood on a date or as it was proposed. Each version
is superseded by the next one and is never redrawn. Policy:
[`.agents/rules/diagram.md`](../../.agents/rules/diagram.md). Procedure: the `diagram` skill
in `.agents/skills/diagram/`.

## Diagram types for this repository

A type appears in `docs/diagram/` from its first version. **Must** types are needed for a
governance gate or a release check. **Nice to have** types are recorded when someone asks.

| Priority | Type | Subject | Shows | Drawn from | Needed by | Index |
|---|---|---|---|---|---|---|
| **Must** | `architecture` | Whole project: phase 1 (GCP test host) and phase 2 (AWS production) in one picture | Components, boundaries, flows, ports | The batch MVP plan, `deploy/` | Gate 4 AF Slide (S3-08), S3-08a | [architecture/](architecture/README.md) |
| **Must** | `data-flow` | `batch-run` | The data that leaves GCP, the processes and stores, the trust boundaries | ADR 0002, the S1-01 schema, S1-08, `deploy/nginx`, the Collector settings | Security Assessment (gates 4 and 6), DPO (gate 3), S2-11 | Not recorded yet |
| **Must** | `sequence` | `batch-run-ingest` | One run from the job to the database and to Langfuse, with one trace ID | `backend/app/api/batch_routes.py`, S1-05, `backend/app/trace_check.py` | S2-08, S4-04 | Not recorded yet |
| Nice to have | `deployment` | Each environment | Where each container runs, with protocol and port | `deploy/compose`, `deploy/langfuse`, the S3-06 files | S3-06, S4-01 | — |
| Nice to have | `er` | `monitor-database` | The tables and their keys | The migrations in `backend/app/db.py` | S1-11, S3-05 | — |
| Nice to have | `state` | `batch-run` | Run status and grade, and what changes them | The S2-05 evaluator, S3-02 | RAI team, S3-02 | — |
| Nice to have | `decision` | `run-grade` | Which grade a run gets, and by which questions | The core metrics | Gate 7 (S4-08) | — |
| Nice to have | `workflow` | Whole project | The 8 governance gates beside the 4 sprints | The governance track in the plan | Project owner | — |
| Nice to have | `use-case` | `monitor` | The actors and what each can do | The plan decisions, S3-07 | VRO Template, BRD | — |

`class` is not used: the domain is small, and the `er` type carries it.

The hand-drawn first drafts of the architecture are in
[`docs/architecture/`](../architecture/README.md).

## Format

Every version is two files with one stem: `NNNN-slug.drawio.svg`, an SVG with the draw.io
model embedded (it renders here and opens in draw.io or VS Code), and `NNNN-slug.md`, from
[`TEMPLATE.md`](TEMPLATE.md). Icons downloaded for the pictures, each with its source, its
license and its SHA-256, are in [`icons/`](icons/README.md).

No diagram contains an IP address, a token or an internal URL.

## Layout

A type with one picture of the whole project keeps its versions in `<type>/`. A type with
one picture per subject (a scenario, an entity, a database) keeps them in
`<type>/<subject>/`, and `<type>/README.md` lists the subjects.

## Numbering

Four digits per directory of versions, sequential, never reused. Find the highest number
and add one:

```bash
ls docs/diagram/<type>/ | grep -E '^[0-9]{4}-' | sort | tail -1
ls docs/diagram/<type>/<subject>/ | grep -E '^[0-9]{4}-' | sort | tail -1
```

## Check

```bash
uv run .agents/skills/diagram/scripts/check_diagrams.py
```

CI runs the same check (`.github/workflows/check-diagrams.yml`). The check needs only
Python. To record a version, draw.io desktop and `uv` are also necessary.
