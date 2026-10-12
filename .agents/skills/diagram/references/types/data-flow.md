# `data-flow`

Answers: **what data moves between which processes, stores, and outside parties, and
where does it cross a trust boundary?** Per subject; the subject is the process the
picture decomposes (`checkout`, `user-import`).

This is a data flow diagram in the strict sense, with its four symbols. Use it when
someone asks for a DFD or a threat model. A request to "show the data flow" between
components is the `architecture` type, whose arrows already are data flows; the
whole-system DFD ("level 0", one process and its outside parties) is what `use-case`
shows, so do not record it here.

Leaves out control (what triggers what), order in time, and decisions: a DFD has no
arrows that mean "then".

Start `0001` from `assets/examples/data-flow.drawio`.

## Draw from

- As built: for the process in the subject, each input it reads (a request body, a
  message, a file, a table), each output it writes, and where each comes from or goes
  to. Trust boundaries come from the deployment and the network: a private network, an
  account, a container's boundary, the line between your code and a third party.
- Proposed: the spec or issue. Name each in `## Sources`.

## Shapes

All with `fontSize=11;strokeColor=#232F3E;fontColor=#232F3E;fillColor=#FFFFFF;`.

| Element | Style | Size |
|---|---|---|
| Process | `ellipse;whiteSpace=wrap;html=1;aspect=fixed;` | 90×90 |
| External entity | `rounded=0;whiteSpace=wrap;html=1;` | 120×60 |
| Data store | `shape=partialRectangle;whiteSpace=wrap;html=1;left=0;right=0;` | 140×40 |

A process is numbered and named verb then object: `1.0&lt;br&gt;Place order`. A store is
numbered too: `D1&amp;nbsp; orders`. An external entity is a person or a system outside
the subject, by name.

Data flow, labelled with the data that moves, a noun (`order details`), never a verb:

```
endArrow=classic;html=1;rounded=0;fontSize=10;strokeColor=#232F3E;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;
```

Two flows between the same pair, one each way, are two edges. Keep them apart with
`exitX`/`exitY` and `entryX`/`entryY` (for example `0.3` on one and `0.7` on the other).

Trust boundary, drawn **first** so everything else sits on top of it. It is not a
container: the cells inside it keep `parent="1"` and absolute coordinates.

```
html=1;fontColor=#DD344C;fontStyle=1;fontSize=10;align=left;verticalAlign=top;spacingLeft=6;spacingTop=2;fillColor=none;dashed=1;strokeWidth=2;strokeColor=#DD344C;rounded=0;
```

Label it with what is trusted inside: `Trust boundary: application network`.

## Layout

- External entities at the left and right edges, processes in the middle, stores to the
  right of the processes that write them.
- At least 130 px between any two shapes a flow connects, so its label fits on the line.
- Every flow that crosses a trust boundary should cross it once, visibly. That crossing
  is what a threat model examines.
- More than about seven processes: split one of them into its own subject, numbered
  under it (`2.1`, `2.2`).

## Rules a DFD must keep

- Every flow has a process at one end at least: no store to store, entity to entity, or
  entity to store.
- Every process has at least one flow in and one flow out.
- Every store is written by something in the picture or is labelled as read-only here.

## A new version when

A process, a store, an external entity, a flow, or a trust boundary is added, removed,
or re-routed. Not for a changed field inside a flow that keeps its name.

## Check the preview

The three rules above hold; no flow label sits on the trust boundary's line; the boundary
encloses exactly the shapes that are trusted together.
