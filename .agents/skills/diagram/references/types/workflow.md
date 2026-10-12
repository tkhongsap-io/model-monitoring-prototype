# `workflow`

Answers: **who does what, in what order, through which stores?** Single by default. A
project with processes that share no steps (a request path and a nightly batch) keeps
them as two titled groups in one picture, or chooses per subject at the first version,
one subject per process.

Shows actors as swimlanes, their steps in order, the decisions that fork the flow, and
the stores a step reads or writes. Leaves out what a component is made of (the
`architecture`) and the message-by-message exchange inside one step (a `sequence`).

Start `0001` from `assets/examples/workflow.drawio`.

## Draw from

The entry points, jobs, pipelines, schedules, and state machines that run, and the
stores they read and write. For a human process, the rule or runbook that describes it.

## Shapes

Swimlane, one per actor, stacked top to bottom, all the same width:

```
swimlane;horizontal=0;startSize=30;html=1;fillColor=#F5F5F5;strokeColor=#9CA3AF;fontStyle=1;fontSize=11;fontColor=#232F3E;container=1;collapsible=0;
```

Step, a child of its lane, numbered in the order it happens, `(1)` … `(n)`:

```
rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#232F3E;fontSize=11;fontColor=#232F3E;
```

A decision is `rhombus;whiteSpace=wrap;html=1;` with the same colours; a store (a topic,
a table, a bucket prefix) is `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=8;`.
Edges are the data and control styles from `drawio.md` section 5, with `parent="1"` even
when both ends are in one lane.

## Layout

- Time runs left to right; a step is to the right of every step before it.
- A step is 140×50; leave 60 px between steps and 30 px above and below them in a lane.
- Put a service's icon beside its first step, not inside every step.
- Two processes that share no steps are two titled groups, never interleaved lanes.

## A new version when

A step, an actor, a decision, or a store is added, removed, or reordered. Not for a
reworded step that does the same thing.

## Check the preview

The numbers run left to right; each step is inside its actor's lane; an edge that changes
lane does so in the gap between two steps.
