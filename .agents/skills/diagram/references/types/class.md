# `class`

Answers: **what are the main things in this part of the domain, and how do they relate?**
Per subject; the subject is a bounded context or module (`ordering`, `billing`).

This is a domain model, not a map of the code. Show the classes a newcomer has to know to
talk about the domain: entities, value objects, the enumerations that drive behaviour.
Leave out methods, and leave out controllers, repositories, DTOs, helpers, and anything
generated. An IDE draws the full class graph on demand and it is out of date the next
day; a picture of twelve domain classes stays true for months.

Start `0001` from `assets/examples/class.drawio`.

## Draw from

- As built: the domain package or module of the subject. A class belongs in the picture
  when other domain classes refer to it or the plan's glossary names it.
- Proposed: the spec or issue. Name each in `## Sources`.

Attributes: only the ones that identify the class or that another class in the picture
is the type of. `id: OrderId` and `status: OrderStatus` earn a row; `updatedAt` does not.

## Shapes

Class (header 26 px, one 24 px row per attribute; height `26 + 24 × rows`):

```
swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=26;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;whiteSpace=wrap;html=1;fontSize=12;fillColor=#F3F4F6;strokeColor=#232F3E;fontColor=#232F3E;swimlaneFillColor=#FFFFFF;
```

Attribute row, a child of the class at `y = 26 + 24 × index` (the export uses the `y`
you write), labelled `name: Type`:

```
text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;html=1;fontSize=11;fontColor=#232F3E;
```

A stereotyped class (an enumeration, an interface, a value object): the same class style
with `fontStyle=0;startSize=40;`, the label
`&amp;laquo;enumeration&amp;raquo;&lt;br&gt;&lt;b&gt;OrderStatus&lt;/b&gt;`, and rows starting at
`y = 40`.

Relations, all `html=1;rounded=0;strokeColor=#232F3E;fontSize=10;fontColor=#232F3E;`
plus:

| Relation | Style | Direction |
|---|---|---|
| Association | `endArrow=none;` | either |
| Directed association | `endArrow=open;endSize=10;` | from the class that holds the reference |
| Composition (the part cannot exist alone) | `endArrow=none;startArrow=diamondThin;startFill=1;startSize=14;` | from the whole |
| Aggregation | the same with `startFill=0;` | from the whole |
| Generalisation | `endArrow=block;endFill=0;endSize=12;` | from the subclass |
| Dependency | `endArrow=open;endSize=10;dashed=1;` | from the dependent |

Class relations are straight lines (no `edgeStyle`). A multiplicity is a label that is a
child of the edge, at its start (`x="-1"`) or its end (`x="1"`, with `align=right` and a
negative offset):

```xml
<mxCell id="e-places-s" value="1" style="edgeLabel;resizable=0;html=1;align=left;verticalAlign=bottom;fontSize=10;fontColor=#232F3E;" connectable="0" vertex="1" parent="e-places">
  <mxGeometry x="-1" relative="1" as="geometry"><mxPoint x="6" y="-2" as="offset"/></mxGeometry>
</mxCell>
```

## Layout

- Classes 170 to 190 wide, at least 120 px apart, so a multiplicity fits at each end.
- The aggregate root in the middle of the top row; what it owns to its right; what it
  refers to below. A superclass above its subclasses.
- More than about twelve classes means two subjects.

## A new version when

A domain class, an attribute shown, or a relation is added, removed, or renamed, or a
multiplicity changes. Not for a method, a private field, or a class the picture leaves
out.

## Check the preview

Each diamond and triangle is at the correct end; multiplicities do not sit on a class
border; no relation passes behind a class.
