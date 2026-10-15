# Intent: one Langfuse project for each use case

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-15)
- **Follows:** S2-03 (#17, closed): self-hosted Langfuse with one project `model-monitor`.
- **Blocks:** S2-08 (#22): the demo shows RTR in its own project.
- **Risk tier:** R1 (identity-only MVP)

## Problem

All traces go to one Langfuse project. In production there will be many use cases from
different sources: GCP batch jobs through our Collector, and later others that send LLM
usage directly (for example from LiteLLM). One shared project becomes unreadable, and each
team must see only its own traces.

## Outcome

The organization "Model monitor" has one project for each use case, named exactly the
`use_case_id`, plus a project `unrouted`. The Collector routes every span to the project of
its use case. All the spans of one run (the job's spans and the backend's spans) and its
scores land in the same project. The evaluator and the trace check use the key pair of the
run's use case.

## Decisions (project owner, 2026-10-15)

| Decision | Reason |
|---|---|
| **Why:** access per team and readability (option C) | Langfuse gives access per project; many use cases from different sources |
| **Build now (B)**, before S2-08 | The demo shows the target shape |
| **Projects are created by hand in the Langfuse UI; a script does the rest.** | Creating projects through the API needs organization API keys, which on self-hosted Langfuse exist only in the Enterprise Edition (paid license). The script writes the keys, checks them against Langfuse, and regenerates the routing. |
| **Project name = `use_case_id`** (A) | A machine can match it; no second name to remember |
| **Spans without a known use case go to a project `unrouted`** (A) | Nothing is lost; the trace check reports it |
| **Routing: resource label `use.case.id`, else span label `use_case_id`, else `service.name` if it is a registered use case** (approach 3) | The resource label is the rule (the job adds it in the S2-04 helper). The `service.name` fallback keeps RTR whole until then: the RTR job's `service.name` is `rtr-fraud-validation`. |
| **One YAML file per project** in `/opt/model-monitor/langfuse-projects/` (folder 700, files 600, root); the script generates the Collector routes and one env file from them | Readable and manageable with hundreds of projects; people never edit generated files |
| Today's project `model-monitor` is renamed `unrouted` and keeps its keys | The switch breaks nothing; the 14 October RTR traces stay there |

Facts from the 14 October RTR trace: only `batch.run` (job) and `monitor.ingest` (backend)
carry `use_case_id`; no span has a use-case resource label. So routing by labels alone would
split the trace today.

## Not in scope

Organization API keys and automatic project creation (Enterprise Edition); LiteLLM sources;
user and member management in Langfuse; a project per environment.

## Success criteria

- CI `collector-routing` proves each routing rule with Collector 0.161.0.
- `langfuse-smoke` still finds 5 of 5, through the per-use-case key lookup.
- On the test host, the next RTR run is 5 of 5 and its trace and scores are in the project
  `rtr-fraud-validation`.
