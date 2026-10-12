# `deployment`

Answers: **where does each part of the software run, and over what do the places talk?**
Single by default: one picture for the environment that matters most, usually production.
A project whose environments differ in shape, not only in size, may choose per subject at
the first version, one subject per environment.

Shows nodes (a cluster, a managed database, a function platform, a device), the
artifacts that run on them, the environment or network that encloses them, and the
protocol and port between them. Leaves out what the components do and how data moves
through them (the `architecture`), and how a release gets there (the `workflow`).

It differs from `architecture` in what a box means: there, a box is a component; here, a
box is a place a component runs. Record a deployment diagram when that mapping is not
one to one or when the network paths matter. Otherwise the architecture already says it.

Start `0001` from `assets/examples/deployment.drawio`.

## Draw from

- As built: infrastructure-as-code, container and orchestration manifests, platform
  configuration, `.github/workflows/` deploy jobs, and the environment's own
  configuration files. Replica counts, regions, and versions go in a label only when the
  code pins them.
- Proposed: the spec or issue. Name each in `## Sources`.

## Shapes

Node, labelled with a stereotype and its name
(`&amp;laquo;node&amp;raquo;&lt;br&gt;Kubernetes cluster`; `&amp;laquo;device&amp;raquo;` for
hardware a person holds). Add `container=1;collapsible=0;` when artifacts sit inside it:

```
verticalAlign=top;align=left;shape=cube;size=10;html=1;boundedLbl=1;spacingLeft=5;whiteSpace=wrap;fontSize=11;fillColor=#FFFFFF;strokeColor=#232F3E;fontColor=#232F3E;
```

Do not add `direction=south` to the cube, as draw.io's own palette does: it turns the
shape's connection points with it, and `entryX=0` then lands on the top face.

Artifact, a child of its node, placed at least 60 px below the node's top so it clears
the label:

```
rounded=0;whiteSpace=wrap;html=1;fontSize=11;fillColor=#F3F4F6;strokeColor=#232F3E;fontColor=#232F3E;
```

with the label `&amp;laquo;artifact&amp;raquo;&lt;br&gt;&lt;b&gt;api&lt;/b&gt;&lt;br&gt;3 replicas`.

Environment, region, or network: the neutral container from `drawio.md` section 4
(`#6B7280`/`#F9FAFB`), or the provider's own group shape (an AWS account, a VPC) when the
node icons are that provider's. A provider's service may be drawn as its icon instead of
a cube; resolve it the way the skill's step 5 says.

Communication path, labelled with the protocol and port (`HTTPS 443`, `TCP 5432`):

```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;fontSize=10;strokeColor=#232F3E;strokeWidth=1.5;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;
```

## Layout

- Left to right from where requests enter: devices and outside networks on the left,
  compute in the middle, stores on the right.
- One container per environment or network boundary; a node sits inside the boundary it
  is deployed in.
- Give every path its own `exitY` and `entryY` when two leave the same artifact or reach
  the same node. Two paths sharing a segment hide each other's labels.

## A new version when

A node, an artifact, an environment, or a path is added, removed, or moved to another
node or network. Not for a replica count, an instance size, or a version.

## Check the preview

Every artifact is inside the node it runs on; every path enters a node from the side it
is drawn toward; no two path labels overlap.
