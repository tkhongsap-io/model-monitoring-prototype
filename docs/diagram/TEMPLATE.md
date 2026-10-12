---
status: current
date: YYYY-MM-DD
author: {git config user.name <user.email>}
related: [ADR-NNNN]
---

# {Type} {subject, if the type has subjects} NNNN: {what the picture shows}

<img src="NNNN-slug.drawio.svg" alt="{Type} NNNN">

{In a record, a Markdown image of the same file is also correct.}

## What it shows

{Two to four sentences: the scope of the picture — what is inside it and what is
deliberately left out. Do not say here whether it is built: `status` says that, and a
proposal that becomes `current` keeps this text.}

## What changed since the previous version

{What was added, removed, or re-routed, and the ADR or change that caused each. For
0001: "First recorded version."}

## Key

{Only what the picture needs: the line styles and markers it uses, what a container
means, the numbering of steps. Omit a row the picture does not use; add the rows its
type needs.}

| Mark | Means |
|---|---|
| Solid dark arrow | Data flow |
| Dashed pink arrow | Control: a trigger, a start, a schedule |
| Dotted grey arrow | Deployment or configuration |

## Sources

{What the picture was drawn from. A `current` version: the files, directories, and ADRs
read. A `proposed` version: the spec, issue, PRD, or conversation.}

- {...}
