# Diagrams

Numbered pictures of the system, as it stood on a date or as it was proposed. Each version
is superseded by the next one and is never redrawn. Policy:
[`.agents/rules/diagram.md`](../../.agents/rules/diagram.md). Procedure: the `diagram` skill
in `.agents/skills/diagram/`.

## Diagram types for this repository

A type appears in `docs/diagram/` from its first version. **Must** types are needed for a
governance gate or a release check. **Nice to have** types are recorded when someone asks.

| Priority | Type | Subject | Shows | Needed by | Index |
|---|---|---|---|---|---|
| **Must** | `architecture` | Whole project: `current` is the GCP test host (phase 1) as it runs; `proposed` is AWS production (phase 2) | Components, boundaries, flows, ports | Gate 4 AF Slide (S3-08), S3-08a | [architecture/](architecture/README.md) |
| **Must** | `data-flow` | `batch-run` | The data that leaves GCP, the processes and stores, the trust boundaries | Security Assessment (gates 4 and 6), DPO (gate 3), S2-11 | [data-flow/](data-flow/README.md) |
| **Must** | `sequence` | `batch-run-ingest` | One run from the job to the database and to Langfuse, with one trace ID | S2-08, S4-04 | [sequence/](sequence/README.md) |
| Nice to have | `deployment` | `gcp-test-host`, `aws-production` | Where each container runs, with protocol and port | S3-06, S4-01 | [deployment/](deployment/README.md) |
| Nice to have | `er` | `monitor-database`, `prototype-tables` | The tables and their keys | S1-11, S3-05 | [er/](er/README.md) |
| Nice to have | `state` | `use-case-delivery` | The delivery health of a use case, and what changes it | RAI team, S3-02 | [state/](state/README.md) |
| Nice to have | `decision` | `run-grade` | Which grade a run gets, and by which questions | Gate 7 (S4-08), S2-05 | [decision/](decision/README.md) |
| Nice to have | `use-case` | `monitor` | The actors and what each can do | VRO Template, BRD | [use-case/](use-case/README.md) |

A version with the status `current` is drawn from the repository. A version with the status
`proposed` is drawn from the plan, for a part that is not built yet: the AWS architecture and
deployment, the delivery state, the run grade and the use cases.

`class` is not used: the domain is small, and the `er` type carries it. `workflow` is not
recorded for now. Record it later if the system gets a process with several actors and
steps (for example the evaluation worker, or the alert path). The governance gates and the
sprints are the project schedule, not the system, so they are not a diagram.

The hand-drawn first drafts of the architecture are in
[`docs/architecture/`](../architecture/README.md).

## Format

Every version is two files with one stem: `NNNN-slug.drawio.svg`, an SVG with the draw.io
model embedded (it renders here and opens in draw.io or VS Code), and `NNNN-slug.md`, from
[`TEMPLATE.md`](TEMPLATE.md). Icons downloaded for the pictures, each with its source, its
license and its SHA-256, are in [`icons/`](icons/README.md).

A version recorded on a machine without draw.io desktop is a Mermaid version: one file,
`NNNN-slug.md`, with `format: mermaid` in its frontmatter and a `mermaid` block that
GitHub draws. It has no product icons and no image file. The next version of that
picture is a draw.io version again when draw.io is available.

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

CI runs the same check on Linux, macOS and Windows
(`.github/workflows/check-diagrams.yml`). The check needs only Python. To record a
draw.io version, draw.io desktop and `uv` are also necessary; this command says whether
draw.io was found:

```bash
uv run .agents/skills/diagram/scripts/render.py doctor
```

Without draw.io desktop, the `diagram` skill records a Mermaid version, which needs only
`uv`.
