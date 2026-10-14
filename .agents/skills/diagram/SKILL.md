---
name: diagram
description: Records a diagram as a numbered draw.io version in docs/diagram/ — architecture, workflow, deployment, use case, sequence, state, ER, class, data flow (DFD), or decision tree — as built from the repository, or as a proposal for a design not built yet. Records it as a Mermaid block when draw.io desktop is not installed. Use when asked to draw, update, or version any diagram of the system; on "diagram", "draw.io", "UML", "ERD", or "DFD"; or when a change adds, removes, or re-routes something a recorded diagram shows.
---

# Record a Diagram Version

Policy: `.agents/rules/diagram.md` — the types, subjects, statuses, and when a version is
due. This skill is the procedure. Two references, read before writing any XML:

- `references/types/<type>.md` — what that type shows, what to read, its shapes and
  layout. Read only the type you are drawing.
- `references/drawio.md` — the file skeleton, house style, icons, containers, edges, and
  pitfalls every type shares.

On a machine without draw.io desktop (step 1 finds out), `references/mermaid.md` takes
the place of `references/drawio.md`.

Paths that start with `references/` or `assets/` are relative to this skill's directory,
`.agents/skills/diagram/`.

## 1. Pick the type, the subject, and the status

**Type.** Choose by the question the picture has to answer, not by the word in the
request. If the user did not name a type, state which you chose and why.

| The picture answers | Type |
|---|---|
| What are the components and boundaries, and what flows across? | `architecture` |
| Who does what, in what order, through which stores? | `workflow` |
| Where does each part run, and over what do the places talk? | `deployment` |
| Who uses the system, and what can each of them do with it? | `use-case` |
| In one scenario, who sends what to whom, in what order? | `sequence` |
| What states can this one thing be in, and what moves it between them? | `state` |
| What is stored, and how do the stored things relate? | `er` |
| What are the main things in this part of the domain? | `class` |
| What data moves between which processes and stores, across which trust boundaries? | `data-flow` |
| Given a case, which outcome does it get, and by which questions? | `decision` |

"Show the data flow" between components is `architecture`; `data-flow` is for a DFD or a
threat model. The system and everyone outside it is `use-case`. Steps over time are
`workflow`; questions and outcomes with no time in them are `decision`.
`docs/diagram/README.md` lists any type the project added.

**Subject.** `architecture`, `workflow`, and `deployment` hold one picture of the whole
project, in `docs/diagram/<type>/`. The other types hold one picture per subject (the
scenario, the entity, the database, the decision), in `docs/diagram/<type>/<subject>/`.
List the subjects that exist and reuse one when the picture is about the same thing; a new
subject is a lowercase slug that names the thing, not the change (`checkout`, not
`add-retry`). A type that already has versions keeps the form it has. Below, `<dir>` is
the directory of versions: `docs/diagram/<type>` or `docs/diagram/<type>/<subject>`.

**Status.** `current` when the picture is of what the repository holds. `proposed` when it
is of a design not built yet: the user says "before we build", "we plan to", "design
for", or the code it would be drawn from does not exist.

**Format.** Find out whether draw.io desktop is here, before any drawing:

```bash
uv run .agents/skills/diagram/scripts/render.py doctor
```

| Exit | Means | Do |
|---|---|---|
| 0 | draw.io was found | Record a draw.io version. This is the format whenever draw.io is installed |
| 1 | draw.io is not installed | Record a **Mermaid version**, and say so now, with the places the command searched |
| 2 | `DRAWIO_BIN` names no file | Stop and report it. Do not fall back: a typing mistake must not change the format |

Mermaid is never a choice of style. If the user asks for Mermaid on a machine that has
draw.io, say that the rule records draw.io there, and ask before you do otherwise.

## 2. Read what is recorded

```bash
ls <dir>/ | grep -E '^[0-9]{4}-' | sort | tail -3
grep -rl --include='*.md' '^status: proposed' docs/diagram/
```

The second command lists every open proposal in the project. Look at each one the change
could have built; step 3 decides what happens to it.

If `<dir>` has a version, read its `.md`, list what it shows, and recover its model to
start from (both only read the recorded file, and neither needs draw.io):

```bash
uv run .agents/skills/diagram/scripts/render.py labels <dir>/NNNN-slug.drawio.svg
uv run .agents/skills/diagram/scripts/render.py extract <dir>/NNNN-slug.drawio.svg <scratch>/current.drawio
```

Starting from the previous model keeps the layout familiar from one version to the next;
a reader comparing versions should see what changed, not a reshuffle. For a first
version, start from `assets/examples/<type>.drawio`: a small picture in the house style
that is known to render.

When the previous version is a Mermaid version (its record has `format: mermaid`),
`labels` takes the `.md` and prints its block, and there is no model to extract. A new
Mermaid version starts from that block. A new draw.io version starts from
`assets/examples/<type>.drawio`, because a block has no layout to keep. When you record a
Mermaid version after a draw.io one, `labels` on the `.drawio.svg` is the list of what
the block must show.

## 3. Establish what the system is now, and decide

A `current` version is drawn from the repository, never from memory. Read `README.md`,
`CLAUDE.md`, the glossary in `changes/2026-10-02-batch-monitoring-mvp/plan.md` for every label, the ADRs in
`docs/adr/` accepted since the current version's `date`, the open plan in `changes/`, and what the type's reference lists under "Draw from". A
`proposed` version is drawn from the spec, issue, PRD, or conversation; keep a list of
them for `## Sources`, and still take every existing name from the repository.

Then decide, and say what you compared:

- **Nothing the current version shows has changed: write nothing.** Each type's
  reference says what counts. A size, a setting, a dependency's version, a refactor, or
  reworded prose never does. A new member of a box that lists its members by name does:
  the picture names it, so the picture is now wrong.
- **A drawing mistake in the `current` version, the system unchanged:** fix it in place
  (re-export over the same file, or correct the block of a Mermaid version).
- **Only the format would change** (the `current` version is Mermaid and draw.io is now
  installed): write nothing, unless the user asks for the draw.io drawing. The next
  version that is due is a draw.io version.
- **An open proposal has now been built.** Compare it with the repository. If it matches
  and it is the highest number in its directory, do not redraw: set its `status` to
  `current`, add `confirmed: <today>` under `date`, set the previous `current` to
  `superseded by NNNN`, update the index rows, and go to step 8. If the build differs or a
  later version exists, record a new version from the repository and set the proposal to
  `superseded by NNNN`.
- **A proposal will not be built:** set it to `withdrawn` and update its index row.
- **Otherwise:** record a new version.

**Check every picture the change touches.** One change often shows in several: a new
component is a box in the architecture, a step in the workflow, a participant in a
sequence. Run `render.py labels` on each `current` version it could affect before saying
it is unaffected. If one is affected and the user asked for another, say so and offer the
second version instead of silently skipping it.

**Offer a type the project does not have** when the change adds what that type shows: the
first schema (`er`), the first state machine (`state`), the first outside actor
(`use-case`). One line, then wait: "This adds the first database schema; record an `er`
diagram for it?" Do not record a first version unasked.

## 4. Number it

The highest number in `<dir>` plus one, four digits; `0001` in a new directory. The slug
describes the picture, lowercase with dashes: `0002-with-streaming-ingest`.

## 5. Resolve every icon

A Mermaid version has no icons: skip this step, and download nothing.

Types drawn in a notation (`use-case`, `sequence`, `state`, `er`, `class`, `data-flow`,
`decision`) use plain shapes and skip this step. For the others, in this order, stopping
at the first that works:

1. The verified styles in `references/drawio.md`, and the icons already in
   `docs/diagram/icons/`.
2. draw.io's built-in libraries, found with the draw.io MCP tool (`search_shapes`) when
   it is available. Besides stencils (`shape=mxgraph.*`), draw.io ships image libraries
   (`image=img/lib/...`: Azure, Dynamics 365, SAP, IBM, Atlassian, …); these are built in
   too. A search result written `image=https://app.diagrams.net/img/lib/...` is shortened
   to `image=img/lib/...`, or `render.py` refuses it. A result from draw.io's icon service
   (`image=https://icons.diagrams.net/...`) is not built in: it is a link, so go on to 3.
3. A download into `docs/diagram/icons/`. Search the web with the tool you have, in this
   order:
   - the provider's own brand or logo page
   - Simple Icons at a pinned version
     (`https://cdn.jsdelivr.net/npm/simple-icons@<version>/icons/<slug>.svg`, or the same
     path under `https://raw.githubusercontent.com/simple-icons/simple-icons/<version>/`),
     with the brand hex from its `data/simple-icons.json`
   - any other website

   Before you download, open the page that states the icon's license or terms.

   **Skip the source**, and do not download it, when:
   - it states no terms
   - it says "free download" without terms
   - it says "personal use only"
   - its terms do not allow use in diagrams

   On a gallery site, the license must be stated for the icon itself, not just for the
   site. Prefer an SVG to a PNG, and a square mark to a wordmark.

   Then download it:

   ```bash
   uv run .agents/skills/diagram/scripts/fetch_icon.py <https-url> <name> [--fill '#RRGGBB']
   ```

   `--fill` is only for a pinned Simple Icons URL. The script runs the **icon check** and
   deletes a refused file, listing why. Never edit a refused file to make it pass; try the
   next source. When nothing passes, the component is a plain labelled shape.

   The script prints a row skeleton. Complete it and add it to
   `docs/diagram/icons/README.md`:
   - **For:** what the icon depicts
   - **License / terms:** the license name, linked to its terms page
   - **Credit:** the text the license asks for, or `—`
   - **Retrieved** and **SHA-256:** copy them as printed

   If the file already existed, the script replaced it; update that row instead of adding
   one.

Add a row for every icon you downloaded, and for every built-in style you verified, to
the icon tables in `references/drawio.md`, so the next version finds it in step 1. A
component with no product icon at all (an in-house system) is a plain labelled shape.

To get the embedding style for a downloaded icon, run the command below. It runs the icon
check again first.

```bash
uv run .agents/skills/diagram/scripts/icon_style.py docs/diagram/icons/<name>.svg --width 48
```

A `.png` works the same way.

## 6. Draw and render

Write the uncompressed mxGraph XML to a scratch `.drawio`, following the type's reference
and the house style. Render it and write a preview:

```bash
uv run .agents/skills/diagram/scripts/render.py export <scratch>/new.drawio \
  <dir>/NNNN-slug.drawio.svg --preview <scratch>/new.png
```

**Look at the PNG** (read it as an image). Check for overlapping labels, edges crossing
shapes, icons that failed to load (an empty square), anything outside its container, and
the points under "Check the preview" in the type's reference. Fix and re-render until it
reads cleanly. The export stops with a message when draw.io is missing, when an icon is
linked by URL or path, or when the file would exceed the 1024 KB limit.

An export that fails when `doctor` found draw.io (on headless Linux, an export without
`xvfb-run` in front) is a failure to report, not a reason to record Mermaid.

**A Mermaid version** (step 1, exit 1) has no export. Write the block, following
`references/mermaid.md`: start from the example of the type, keep the type's keyword on
the first line, and quote every label that has punctuation. Nothing renders the block
here, so read the text for each point in section 4 of that reference in place of the
preview. The block goes into the record in step 7; no `.drawio.svg` is written.

## 7. Write the record

- Copy `docs/diagram/TEMPLATE.md` to `<dir>/NNNN-slug.md` and fill it: `status` (`current`
  or `proposed`), `date` today, `author` from `git config user.name` and
  `git config user.email` as `Name <email>`, `related` ADRs (`[]` when none); what it
  shows; what changed since the previous version (for 0001, "First recorded version");
  the key, with the rows this type's marks need; the sources from step 3.
- A Mermaid version: add `format: mermaid` under `related` in the frontmatter, and put
  the block where the template has the image. Remove the image line.
- A new `current` version: set the previous `current` to `superseded by NNNN`. A new
  `proposed` version: leave the `current` one alone, since it is still the picture of the
  repository; set an earlier open proposal it replaces to `superseded by NNNN`. A version
  that is no longer `current` or `proposed` is history: change its `status` and nothing
  else.
- Add the row to `<dir>/README.md` and set the previous row's status.
- A new subject: create `<dir>/README.md` (title, one line saying what the subject is,
  the version table) and add the subject's row to `docs/diagram/<type>/README.md`,
  linking `<subject>/README.md`.
- A new type: create `docs/diagram/<type>/README.md` and add the type's row to
  `docs/diagram/README.md`. Copy the shape of the existing type indexes.
- If `README.md` links to the current diagram, point the link at the new version.

## 8. Close

If you wrote anything, run the structural check (CI runs the same check in
`.github/workflows/check-diagrams.yml`), then the checks in `TESTING.md` that the change
needs:

```bash
uv run .agents/skills/diagram/scripts/check_diagrams.py
```

Report what passed, failed, and was not run, and list the proposals still open. For a
Mermaid version, the report also says that draw.io was not found and where the command
searched, that no rendered picture was inspected, that the first rendered view is the
record on GitHub after a push, and that the version has no product icons and no image
file. A diagram
version on its own is not a `CHANGELOG.md` item, and neither is a new icon: the change the
picture depicts carries the entry. If that change has no entry yet, say so.
