# `architecture`

Answers: **what are the components, where are the boundaries between them, and what
flows across?** Single by default. A repository that holds two systems with no shared
components may choose per subject at the first version, one subject per system.

Shows components (services, jobs, stores, queues, outside systems), the boundaries they
sit in (a provider, an account, a network, a repository), and the data and control that
pass between them. Leaves out the order things happen in (the `workflow`) and what is
inside a component.

Start `0001` from `assets/examples/architecture.drawio`.

## Draw from

The components themselves: top-level source directories and their manifests,
infrastructure-as-code, container and deployment files, `.github/workflows/`, and
whatever else declares a component, a dependency, or a boundary. `docs/prd/` gives the
system's edges: what is in and out of scope.

## Shapes

Everything in `drawio.md`: the label convention and icons (sections 2 and 3), containers
(section 4), and the four edge meanings (section 5). A component with a product icon is
that icon; one without is a rounded rectangle:

```
rounded=1;whiteSpace=wrap;html=1;fontSize=11;fillColor=#FFFFFF;strokeColor=#232F3E;fontColor=#232F3E;
```

A store with no product icon:

```
shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=10;fontSize=11;fillColor=#FFFFFF;strokeColor=#232F3E;fontColor=#232F3E;
```

## Layout

- Left to right is the direction of data: sources and callers on the left, stores and
  consumers on the right.
- One container per boundary, nested when the boundaries are (a network inside an
  account). An outside service that acts on something gets its own container beside it.
- A legend in the bottom-left corner when more than one edge style is used: one short
  sample edge per style, with its meaning as the label.

## A new version when

A component, a boundary, or a flow is added, removed, or re-routed, or a box that lists
its members by name gains or loses one. Not for a size, a setting, a version, or a
refactor inside a component.

## Check the preview

Every component is inside the boundary it belongs to; no edge crosses a box it does not
connect; every icon rendered (an empty square is a failed image).
