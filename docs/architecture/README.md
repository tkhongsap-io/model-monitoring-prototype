# Architecture diagrams (first draft)

These diagrams are the first draft of the batch monitoring MVP architecture for S3-08a
([#81](https://github.com/tkhongsap-io/model-monitoring-prototype/issues/81)). The team
uses them to consult K. Wirat and the other teams before the IT Solution Architecture
review forum (gate 4, S3-08,
[#76](https://github.com/tkhongsap-io/model-monitoring-prototype/issues/76)). After the
consultation, they are the input for the AF Slide.

| Diagram | Shows |
|---|---|
| [GCP test host](architecture-gcp-compute-engine.drawio.svg) | Sprints 1 to 3: one Compute Engine VM with Docker Compose, a private VPC path from the GCP jobs, no external IP |
| [AWS production](architecture-aws.drawio.svg) | Sprint 4, plan A: the components on the AWS Kubernetes cluster and the data flow |
| [AWS production detail](architecture-aws-production-detail.drawio.svg) | Proposed for discussion: the Thailand region, two availability zones, network, security, logging, backup and DR |

Each file is an SVG with the draw.io source in it. To edit a diagram, open the file in
draw.io (diagrams.net) and save it again as `.drawio.svg`.

## Check during the consultation

- The diagrams show the October scope: identity-only, no customer text and no judge
  (decision of 2026-10-09). The judge calls and the Token Factory (the judge model) are
  removed. They come back in a later version, after October.
- The source of truth for the design is
  [the batch MVP plan](../../changes/2026-10-02-batch-monitoring-mvp/plan.md). If a diagram
  and the plan are different, record the difference in #81.
