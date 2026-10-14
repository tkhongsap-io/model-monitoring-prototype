# `sequence`

Answers: **in one scenario, who sends what to whom, in what order?** Per subject; the
subject is the scenario (`password-reset`, `checkout`).

Leaves out: branches that belong to another scenario (give them their own subject), what
happens inside a participant, and data shapes. More than about eight participants or
twenty messages means two scenarios.

Start `0001` from `assets/examples/sequence.drawio`.

## Draw from

- As built: the entry point of the scenario (a route, a handler, a job, a CLI command)
  and every call it makes across a boundary: another service, a queue, a store, a
  third-party API. Follow the code; a call the code does not make is not a message.
- Proposed: the spec, issue, or conversation. Name each in `## Sources`.

A participant is something with its own boundary: a person, a service, a store, an
outside system. Use the names the architecture diagram and the plan's glossary use. A module or
a class inside one service is not a participant.

## Shapes

Lifeline (a participant; the box is the top 40 px, the dashed line the rest):

```
shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;dropTarget=0;collapsible=0;recursiveResize=0;outlineConnect=0;portConstraint=eastwest;size=40;fontSize=11;strokeColor=#232F3E;fontColor=#232F3E;fillColor=#FFFFFF;
```

A person: the same with `participant=umlActor;size=50;verticalAlign=top;spacingTop=52;`,
30 wide instead of 110.

Activation bar, a child of its lifeline (`parent` = the lifeline, `x` = half the
lifeline's width minus 5, `width` 10):

```
html=1;points=[[0,0,0,0,5],[0,1,0,0,-5],[1,0,0,0,5],[1,1,0,0,-5]];perimeter=orthogonalPerimeter;outlineConnect=0;targetShapes=umlLifeline;portConstraint=eastwest;fillColor=#FFFFFF;strokeColor=#232F3E;
```

Messages are edges with **no `source` or `target`**: each carries its two ends as
absolute points, so it stays horizontal at its own `y` whatever the router would do.

```xml
<mxCell id="m2" value="2 POST /password-resets" style="html=1;verticalAlign=bottom;endArrow=block;endFill=1;rounded=0;fontSize=10;strokeColor=#232F3E;labelBackgroundColor=#FFFFFF;" edge="1" parent="1">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="260" y="200" as="sourcePoint"/>
    <mxPoint x="470" y="200" as="targetPoint"/>
  </mxGeometry>
</mxCell>
```

| Message | Style change |
|---|---|
| Synchronous call | `endArrow=block;endFill=1;` |
| Asynchronous: sent without waiting | `endArrow=open;endFill=0;` |
| Return | `endArrow=open;endSize=8;dashed=1;` |

A fragment (`alt`, `opt`, `loop`) is a frame drawn before the lifelines it spans, its
label the operator and the guard (`alt [token valid]`):

```
shape=umlFrame;whiteSpace=wrap;html=1;pointerEvents=0;width=90;height=22;fontSize=10;strokeColor=#6B7280;fontColor=#232F3E;fillColor=#F3F4F6;swimlaneFillColor=none;
```

## Layout

- Lifelines left to right in the order they first take part, 220 px between their
  centres, all starting at the same `y` and ending below the last message.
- Messages top to bottom, 40 to 50 px apart, each numbered in its label (`1 submit
  email`). An end's `x` is the lifeline's centre, or the near edge of the activation bar
  when there is one (centre ± 5).
- An activation bar runs from the message that starts the work to the return that ends it.
- A frame's left edge sits in the gap between two lifelines, never on one: its label tab
  is in the top-left corner and a dashed line through it cuts the text.

## A new version when

A participant or a message is added, removed, or reordered, or a message changes from
synchronous to asynchronous. Not for a renamed parameter or a changed payload field.

## Check the preview

Every message is horizontal and ends on a lifeline; no label sits on a dashed line it does
not belong to; the numbers run in order from the top.
