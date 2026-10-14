# `er`

Answers: **what is stored, and how do the stored things relate?** Per subject; the
subject is one database or schema (`shop`, `billing`).

Shows every table with its primary key, its foreign keys, and its column names, in crow's
foot notation. Leaves out data types, defaults, indexes, and constraints other than keys:
they change often and the schema file is the place to read them.

Start `0001` from `assets/examples/er.drawio`.

## Draw from

- As built: the schema as the code declares it. In order of trust: migration files
  applied in order, a schema dump or DDL file, ORM model definitions. Read all of them;
  when two disagree, the migrations win and the disagreement goes in your report.
- Proposed: the spec or issue. Name each in `## Sources`.

A relationship is drawn only where a foreign key (or the ORM's equivalent) declares it.
Optionality comes from nullability: a nullable foreign key is "zero or one" on the
referenced side.

## Shapes

Table (header 26 px, then one 24 px row per column; set the height to `26 + 24 × rows`):

```
swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=26;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;align=center;fontSize=12;whiteSpace=wrap;html=1;fillColor=#F3F4F6;strokeColor=#232F3E;fontColor=#232F3E;swimlaneFillColor=#FFFFFF;
```

Row, a child of the table at `y = 26 + 24 × index`, as wide as the table. draw.io lays the
rows out when the file is edited, but the export uses the `y` you wrote, so write it:

```
text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=11;whiteSpace=wrap;html=1;fontColor=#232F3E;
```

Row labels: `<b>PK</b>&nbsp; id`, `<b>FK</b>&nbsp; customer_id`, and for a plain column
three `&nbsp; ` then the name, so the names line up. Keys first, then the other columns in
schema order.

Relationship, from the **row** holding the referenced key to the **row** holding the
foreign key, so the line lands on the column it is about:

```
edgeStyle=entityRelationEdgeStyle;html=1;rounded=0;strokeColor=#232F3E;strokeWidth=1.5;startSize=10;endSize=10;startArrow=<marker>;endArrow=<marker>;
```

| Marker | Means |
|---|---|
| `ERmandOne` | exactly one |
| `ERzeroToOne` (add `startFill=0;` or `endFill=0;`) | zero or one |
| `ERoneToMany` | one or more |
| `ERzeroToMany` (add `startFill=0;` or `endFill=0;`) | zero or more |

The usual foreign key is `startArrow=ERmandOne;` on the referenced row and
`endArrow=ERzeroToMany;endFill=0;` on the foreign-key row. A relationship needs no label;
the two column names say what it is.

## Layout

- Tables 180 wide, at least 120 px apart horizontally and 80 px vertically, so the
  markers have room.
- Put a referenced table to the left of the tables that reference it. A table referenced
  from two sides goes in the middle.
- More than about twelve tables: split by subject, and show a table from the other
  subject as a header-only box (no rows) with a grey stroke `#6B7280`.

## A new version when

A table, a key, a column, or a relationship is added, removed, or renamed, or a
relationship's cardinality changes. Not for a changed data type, default, or index.

## Check the preview

Every relationship line ends on a key row, not on a header or a blank area; no marker is
hidden under a table; no line runs through a table it does not connect.
