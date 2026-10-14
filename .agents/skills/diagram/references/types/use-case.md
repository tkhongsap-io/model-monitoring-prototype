# `use-case`

Answers: **who uses the system, and what can each of them do with it?** Per subject; the
subject is the system or the part of it the boundary encloses (`storefront`,
`back-office`).

This type also carries the system's context: the boundary box is the system, and
everything outside it, people and other systems alike, is an actor. There is no separate
context diagram.

Leaves out how a use case works (that is a `sequence`), the order use cases happen in
(the `workflow`), and anything inside the boundary that is not something an actor does.

Start `0001` from `assets/examples/use-case.drawio`.

## Draw from

- As built: the entry points an outsider can reach: routes and pages, API operations,
  CLI commands, scheduled jobs that act for someone, webhooks received. Group them by the
  goal they serve; one use case is one goal ("Place order"), not one endpoint. Actors
  come from the roles in the authorisation code and from the outside systems the code
  calls or is called by. `docs/prd/` names the consumers.
- Proposed: the spec, the PRD, or the conversation. Name each in `## Sources`.

## Shapes

All with `strokeColor=#232F3E;fontColor=#232F3E;`.

System boundary, drawn first, labelled with the system's name:

```
rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;align=center;fontStyle=1;fontSize=12;spacingTop=6;fillColor=#F9FAFB;container=1;collapsible=0;
```

Use case, a child of the boundary, 160×60, named verb then object:

```
ellipse;whiteSpace=wrap;html=1;fontSize=11;fillColor=#FFFFFF;
```

Actor, outside the boundary, 30×60:

```
shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fontSize=11;fillColor=#FFFFFF;
```

An actor that is a system, not a person, carries a stereotype in its label:
`&amp;laquo;system&amp;raquo;&lt;br&gt;Payment provider`.

| Line | Style |
|---|---|
| Actor takes part in a use case | `endArrow=none;html=1;rounded=0;` |
| `«include»`: the first always runs the second | `endArrow=open;endSize=8;dashed=1;html=1;rounded=0;fontSize=10;labelBackgroundColor=#F9FAFB;`, from the including use case, labelled `&amp;laquo;include&amp;raquo;` |
| `«extend»`: the first sometimes adds to the second | the same, from the extending use case, labelled `&amp;laquo;extend&amp;raquo;` |
| One actor is a kind of another | `endArrow=block;endFill=0;endSize=12;html=1;rounded=0;`, from the specific actor |

## Layout

- The boundary in the middle. Actors who start use cases on the left, actors the system
  calls on the right.
- Use cases in one column inside the boundary, 30 px apart, ordered so each actor's lines
  do not cross: an actor sits level with the middle of the use cases it touches.
- More than about ten use cases means two subjects.

## A new version when

An actor or a use case is added, removed, or renamed, or an actor gains or loses a use
case. Not for a change in how a use case works.

## Check the preview

Every use case is inside the boundary and every actor outside it; every use case has at
least one actor, directly or through an include; lines do not cross a use case they do
not belong to.
