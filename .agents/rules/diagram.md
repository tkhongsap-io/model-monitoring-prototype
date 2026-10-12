# Diagram Versions

Diagrams live in `docs/diagram/` as **diagram versions**: numbered pictures of one aspect
of the system, as it stood on a date or as it was proposed, superseded by the next
version and never redrawn. An ADR records why the system is shaped the way it is; a
diagram version records what that shape was. The rule and the skill come from
`project-template` (S3-08b, `changes/2026-10-13-s3-08b-diagram-skill/`).

## Types

A type is chosen by the question the picture answers, not by the word in the request.

| Type | Answers | Default |
|---|---|---|
| `architecture` | What are the components, where are the boundaries, and what flows across? | single |
| `workflow` | Who does what, in what order, through which stores? | single |
| `deployment` | Where does each part run, and over what do the places talk? | single |
| `use-case` | Who uses the system, and what can each of them do with it? | per subject |
| `sequence` | In one scenario, who sends what to whom, in what order? | per subject |
| `state` | What states can this one thing be in, and what moves it between them? | per subject |
| `er` | What is stored, and how do the stored things relate? | per subject |
| `class` | What are the main things in this part of the domain, and how do they relate? | per subject |
| `data-flow` | What data moves between which processes and stores, across which trust boundaries? | per subject |
| `decision` | Given a case, which outcome does it get, and by which questions? | per subject |

Three lines that are easy to blur:

- "Show the data flow" between components is `architecture`. `data-flow` is a data flow
  diagram in the strict sense, for when a DFD or a threat model is asked for.
- The system and everyone outside it is `use-case`: its boundary is the system, and
  people and outside systems are its actors. There is no separate context type.
- Steps over time are `workflow`. Questions and outcomes with no time in them are
  `decision`. Why the project chose one design over another is an ADR, not a diagram.

`class` is a domain model: the main classes of a domain with the attributes that identify
them, no methods. `er` shows every table, its keys, and its column names, no data types.

**Types are opt-in.** A project has a type from the day it records the type's first
version; none is required. A project adds a type of its own by adding the directory, its
`README.md` index, and a row in `docs/diagram/README.md`, and needs a reason the ten
above cannot carry.

## Subjects

A **single** type holds one picture of the whole project: `docs/diagram/<type>/`. A
**per-subject** type holds one picture per **subject**, the part of the system the picture
is about (a scenario, an entity, a database, a decision): `docs/diagram/<type>/<subject>/`.
The subject is a lowercase slug with dashes.

Each directory of versions has its own number sequence and its own `README.md` index. A
per-subject type's `README.md` lists its subjects.

The table gives each type's default. A project may choose the other form when it records
the type's first version (two systems in one repository, each with its own
`architecture`), and then keeps it: moving versions between directories breaks every link
to them. A type directory never holds both versions and subject directories.

## Status

| Status | Means |
|---|---|
| `current` | The picture of what the repository holds now |
| `proposed` | The picture of a design not built yet |
| `superseded by NNNN` | A later version in the same directory replaced it |
| `withdrawn` | A proposal that will not be built |

A directory of versions has at most one `current` and at most one `proposed`.

A `current` version is drawn from the repository, never from memory. A `proposed` version
is drawn from a spec, an issue, a PRD, or a conversation, and its `## Sources` names them.

When the proposed design is built, compare the proposal with the repository:

- **It matches, and the proposal is the highest number in its directory:** change its
  `status` to `current`, add `confirmed: YYYY-MM-DD` (the day it was compared), and set
  the previous `current` to `superseded by NNNN`. The drawing and the `date` stay.
- **The build differs, or a later version exists:** record a new version from the
  repository, and set the proposal to `superseded by NNNN`.
- **The design is dropped:** set the proposal to `withdrawn`. It stays as history.

A proposal does not supersede the `current` version until it becomes `current` itself.

## When to record a new version

**Record one** when something the current version shows is added, removed, or re-routed:

| Type | A new version when this changes | Not when |
|---|---|---|
| `architecture` | a component, a boundary, a flow, a named member of a box | a size, a setting, a version, a refactor |
| `workflow` | a step, an actor, a decision, a store | a step is reworded |
| `deployment` | a node, an artifact, an environment, a path | a replica count, an instance size, a version |
| `use-case` | an actor, a use case, who takes part in which | how a use case works |
| `sequence` | a participant, a message, their order | a parameter or a payload field |
| `state` | a state, a transition, a guard that changes the path | an action that leaves the states alone |
| `er` | a table, a key, a column, a relationship, a cardinality | a data type, a default, an index |
| `class` | a domain class, an attribute shown, a relation, a multiplicity | a method, a private field |
| `data-flow` | a process, a store, an external entity, a flow, a trust boundary | a field inside a flow |
| `decision` | a question, a branch, an outcome, a threshold | a label is reworded |

**Record nothing** when the change does not alter what the picture shows. Say what you
compared.

**Fix in place** a drawing mistake in the `current` version when the system did not
change: re-export over the same file. A superseded or withdrawn version is never edited:
it is history.

**Check every picture the change touches.** One change often shows in several: a new
component is a box in the architecture, a step in the workflow, a node in the deployment,
a participant in a sequence. Look at each `current` version, and at each `proposed`
version the change may have just built.

**Offer a type the project does not have yet** when a change adds what that type shows:
the first schema, the first state machine, the first outside actor. Say so in one line and
wait for the answer. Never record a first version unasked.

A project's first version of any type is recorded when there is something real to draw,
not at initialization.

## Format

- Two files per version, same stem: `NNNN-slug.drawio.svg` (an SVG with the draw.io model
  embedded, uncompressed, so it renders in Markdown, opens in draw.io, and diffs as text)
  and `NNNN-slug.md` from `docs/diagram/TEMPLATE.md`
- Four-digit numbers per directory of versions, sequential, **never reused**. The slug
  describes the picture, lowercase with dashes
- Frontmatter: `status`, `date` (ISO 8601, the day the version was recorded), `author`
  (`git config user.name` / `user.email` as `Name <email>`), `related` (ADRs), and
  `confirmed` on a proposal that became `current`
- Changing a version's status changes only its `status`, `confirmed`, and its index row,
  nothing else
- Labels use the names in the glossary in `changes/2026-10-02-batch-monitoring-mvp/plan.md`
  and the names the code and infrastructure use
- Every image is embedded: a data URI, or draw.io's own `img/lib/...` library. Never a URL
  or a file path — the next edit would depend on the network or on one machine's disk

## Icons

Resolved in this order, stopping at the first that works:

1. the styles already verified in the skill's reference
2. draw.io's built-in libraries
3. a download into `docs/diagram/icons/` from the provider's own page
4. a download from Simple Icons at a pinned version
5. a download from any other website that states a license or terms for that icon

A component with no product icon is a plain labelled shape, never an unrelated logo.

**A downloaded icon** follows these rules:

- It is an SVG or a PNG of at most 100 KB, and a PNG is at most 1024 px on each side.
- It enters only through the skill's `fetch_icon.py`.
- It passes the **icon check** (`icon_safety.py`), at download and in CI. The check
  refuses script, event handlers, HTML, and DTDs; links that leave the file; and PNG
  location data, unknown chunks, and bytes after the image. A file that fails is
  refused, never repaired: try the next source.
- It is kept byte for byte as downloaded, except that an SVG ends in exactly one
  newline. A Simple Icons SVG may also get the brand `fill` on its root element. A file
  under no-derivatives or "do not alter" terms gets no other change.
- Its license must allow use in this repository's diagrams. A license that asks for
  credit is fine. A page with no terms, "free download" with no terms, or "personal use
  only" means the icon is not used.
- It has a row in `docs/diagram/icons/README.md` with its source URL, the license and
  the URL of its terms, the credit the license asks for, the date retrieved, and its
  SHA-256. The check fails when the file's hash does not match its row.
- When the provider changes its logo, the file is replaced in place, and its row gets the
  new source, date, and hash. Earlier diagram versions keep the copy embedded in them.

## Tooling

Recording a version needs draw.io desktop (`DRAWIO_BIN` if it is not in the default
place; `xvfb-run` in front of it on headless Linux) and `uv`. Reading one needs nothing: it
is an SVG. `check_diagrams.py` checks the records' structure without draw.io; CI runs it
in `.github/workflows/check-diagrams.yml`.

## Changelog

A diagram version on its own is not a changelog item; the change it depicts carries the
entry. Neither is a new icon.

## Procedure

The `diagram` skill records a version: it picks the type and the subject, reads the
current version, establishes what the system is now, decides whether anything changed,
draws, renders, inspects the preview, and writes the record.
