# `state`

Answers: **what states can this one thing be in, and what moves it between them?** Per
subject; the subject is the thing that has the states (`order`, `subscription`, `job`).

Leaves out what happens inside a state and who triggers an event (that is a `sequence` or
the `workflow`). One picture is one entity; two entities whose states affect each other
are two subjects.

Start `0001` from `assets/examples/state.drawio`.

## Draw from

- As built: the status enumeration or state column of the entity, then every place the
  code assigns it. Each assignment is a transition: its source is the state the code
  checks or requires first, its event is the function or message that runs it, and its
  guard is the condition around it. A state-machine library's definition, when there is
  one, is the whole answer.
- Proposed: the spec or issue. Name each in `## Sources`.

A state nothing transitions into, or a transition the code cannot take, is a finding:
report it, and draw what the code does.

## Shapes

All with `strokeColor=#232F3E;fontColor=#232F3E;`.

| Element | Style | Size |
|---|---|---|
| State | `rounded=1;arcSize=30;whiteSpace=wrap;html=1;fontSize=11;fillColor=#FFFFFF;` | 120×50 |
| Initial pseudostate | `ellipse;html=1;aspect=fixed;fillColor=#232F3E;` | 20×20 |
| Final state | `ellipse;html=1;shape=endState;aspect=fixed;fillColor=#232F3E;` | 24×24 |
| Choice | `rhombus;whiteSpace=wrap;html=1;fontSize=10;fillColor=#FFFFFF;` | 40×40 |

Transition:

```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;endSize=8;verticalAlign=bottom;fontSize=10;strokeColor=#232F3E;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;
```

Its label is `event [guard] / action`, each part only when it exists: `pay [authorised]`,
`refund / release stock`. The edge out of the initial pseudostate and the edge into a
final state carry no label.

A composite state (states nested in a state) is a container drawn before its children,
with the children's `parent` set to it:

```
rounded=1;arcSize=6;whiteSpace=wrap;html=1;verticalAlign=top;align=left;spacingLeft=10;spacingTop=6;fontStyle=1;fontSize=11;fillColor=#F9FAFB;strokeColor=#232F3E;fontColor=#232F3E;container=1;collapsible=0;
```

## Layout

- The main path (the states most instances pass through) in one row, left to right,
  220 px between the left edges of neighbouring states, so a transition label fits.
- Exceptional states (cancelled, failed, expired) in a second row below, each under the
  state it is most often reached from.
- One final state per way of ending. Do not route two endings into one circle across the
  picture.
- Where two transitions would share a segment, give one of them `exitX`/`exitY` and
  `entryX`/`entryY` so they leave and arrive at different points.

## A new version when

A state or a transition is added, removed, or renamed, or a guard changes which
transition is taken. Not for a changed action that leaves the states alone.

## Check the preview

Every state can be reached from the initial pseudostate; every transition has an arrow
head at one end only; no label sits on top of another transition.
