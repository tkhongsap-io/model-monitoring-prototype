# draw.io for recorded diagrams

Everything every diagram type shares: what is needed to write a diagram's XML by hand and
have it render the same in draw.io, VS Code and GitHub. The shapes and layout of one type
are in `types/<type>.md`. The styles here and there were rendered and checked with draw.io
desktop (29.6.1, and 29.2.9 for the type references).

## Contents

1. The file skeleton
2. House style
3. Verified icon styles
4. Containers
5. Edges
6. Pitfalls

## 1. The file skeleton

Write **uncompressed** XML (draw.io reads either; uncompressed can be read and edited
here). Every cell has a unique `id`; `0` and `1` are the two root cells every model needs.
A cell inside a container sets `parent` to the container's id, and its `x`/`y` are then
relative to the container.

```xml
<mxfile host="drawio">
  <diagram id="architecture" name="Architecture 0001">
    <mxGraphModel background="#FFFFFF" grid="1" gridSize="10" page="0" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- containers first, then icons, then edges, so edges draw on top -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

(The comment above is for this document. Put no XML comments in the file itself; some
draw.io importers reject them.)

Attribute values are XML: escape `&` as `&amp;`, `<` as `&lt;`, `"` as `&quot;`. An HTML
label (`html=1`) such as `MSK<br>orders.events` is written `MSK&lt;br&gt;orders.events`.

## 2. House style

- **One palette.** Lines and text `#232F3E`; a shape's fill `#FFFFFF`; a header or a
  quiet fill `#F3F4F6`; a neutral boundary `#6B7280` on `#F9FAFB`; secondary text
  `#6B7280`. Notation diagrams (use case, sequence, state, ER, class, data flow, decision)
  use nothing else, except the red `#DD344C` of a trust boundary and the blue
  `#2088FF`/`#F0F7FF` of a decision's outcome. Colour beyond that belongs to a provider's
  icons and containers.
- **Light theme on white.** Set `background="#FFFFFF"` for the app; the export ignores it,
  so `render.py` forces the light theme and a white background itself. draw.io would
  otherwise write adaptive `light-dark()` colours on a transparent background, which can
  turn dark text onto a dark page.
- **Label = what it is, then its name**, from the glossary in `changes/2026-10-02-batch-monitoring-mvp/plan.md` and the names the code and
  infrastructure use: `Lambda<br>orders-ingest`. When the repository has several
  modules, packages, or infrastructure roots, a third, smaller line names the one that
  owns the component, in grey:
  `&lt;font style=&quot;font-size:9px&quot; color=&quot;#6B7280&quot;&gt;infra/platform&lt;/font&gt;`.
- **Icons 48×48** on a 10 px grid, at least 120 px apart horizontally, so labels of two
  lines do not collide.
- **Left to right is the direction of data**: sources and callers on the left, stores
  and consumers on the right.
- **A legend** in the bottom-left corner when the diagram uses more than one edge style.
- **Title** as a text cell at the top-left: the type, the subject when there is one, the
  number and what the picture shows in bold, then the date
  (`text;html=1;align=left;verticalAlign=top;fontSize=12;fontColor=#232F3E;`). Nothing in
  the drawing says `proposed`: the record's `status` does, and a proposal that becomes
  `current` keeps its drawing.

## 3. Verified icon styles

### AWS services (built in: `mxgraph.aws4.resourceIcon`)

All share this prefix; only `fillColor` (the AWS category colour) and `resIcon` change:

```
sketch=0;outlineConnect=0;fontColor=#232F3E;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;aspect=fixed;shape=mxgraph.aws4.resourceIcon;fillColor=<colour>;resIcon=mxgraph.aws4.<name>;
```

| Service | `resIcon` | `fillColor` |
|---|---|---|
| Lambda | `lambda` | `#ED7100` |
| ECS | `ecs` | `#ED7100` |
| Fargate | `fargate` | `#ED7100` |
| MSK (Managed Streaming for Apache Kafka) | `managed_streaming_for_kafka` | `#8C4FFF` |
| Managed Service for Apache Flink (draw.io still names it Kinesis Data Analytics) | `kinesis_data_analytics` | `#8C4FFF` |
| RDS (for PostgreSQL) | `rds` | `#C925D1` |
| S3 | `s3` | `#7AA116` |
| Step Functions | `step_functions` | `#E7157B` |
| CloudWatch | `cloudwatch` | `#E7157B` |
| KMS | `key_management_service` | `#DD344C` |
| Secrets Manager | `secrets_manager` | `#DD344C` |
| IAM | `identity_and_access_management` | `#DD344C` |
| PrivateLink (VPC endpoints) | `vpc_privatelink` | `#8C4FFF` |
| EKS | `eks` | `#ED7100` |
| Shield | `shield` | `#DD344C` |
| WAF | `waf` | `#DD344C` |
| IAM Identity Center (draw.io still names it Single Sign-On) | `single_sign_on` | `#DD344C` |
| Route 53 | `route_53` | `#8C4FFF` |
| Data Firehose (draw.io still names it Kinesis Data Firehose) | `kinesis_data_firehose` | `#8C4FFF` |
| CloudWatch (the newer icon) | `cloudwatch_2` | `#E7157B` |
| CloudTrail | `cloudtrail` | `#E7157B` |
| AWS Backup | `backup` | `#7AA116` |

Colours are AWS's category colours: compute `#ED7100`, analytics and networking
`#8C4FFF`, database `#C925D1`, storage `#7AA116`, application integration and management
`#E7157B`, security `#DD344C`.

### AWS resource shapes (outline icons: `shape=mxgraph.aws4.<name>`)

For a resource inside a service (a topic, a bucket, an endpoint):

```
sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;aspect=fixed;pointerEvents=1;fillColor=<colour>;shape=mxgraph.aws4.<name>;
```

Verified names: `endpoint`, `endpoints`, `peering`, `topic`, `generic_database`, `bucket`,
`role`, `users`, `application_load_balancer`, `nat_gateway`, `internet_gateway`. Use the
parent service's colour (`#8C4FFF` for the networking shapes).

### Google Cloud services (built in: `mxgraph.gcp2.hexIcon`)

All share this style; only `prIcon` changes. The label goes below the icon, 54 by 48:

```
sketch=0;html=1;fillColor=#5184F3;strokeColor=none;verticalAlign=top;labelPosition=center;verticalLabelPosition=bottom;align=center;fontSize=11;fontColor=#232F3E;shape=mxgraph.gcp2.hexIcon;prIcon=<name>;
```

Verified `prIcon` names: `cloud_sql`, `cloud_nat`, `cloud_dns`, `identity_aware_proxy`,
`compute_engine`, `cloud_run`, `container_registry`. `artifact_registry` does not exist as a
`prIcon`: use the Artifact Registry image of draw.io's GCP icon library (a data URI; architecture
0002 has it). A
Google Cloud project or VPC is a rounded container with the stroke `#4285F4` and the fill
`#F0F6FF`.

### draw.io image libraries (built in: `image=img/lib/...`)

draw.io also ships icon sets as images rather than stencils: `img/lib/azure2/`,
`img/lib/mscae/`, `img/lib/dynamics365/`, `img/lib/sap/`, `img/lib/ibm/`,
`img/lib/atlassian/` and others. They count as built in: the export embeds the rendered
image, and every copy of draw.io resolves the path when the file is edited. Write the
path relative (`img/lib/...`); the `https://app.diagrams.net/img/lib/...` form the shape
search returns is refused by `render.py`.

```
image;aspect=fixed;html=1;points=[];align=center;fontSize=11;verticalLabelPosition=bottom;verticalAlign=top;image=img/lib/<set>/<file>.svg;
```

| Product | `image=` |
|---|---|
| Dynamics 365 | `img/lib/dynamics365/Dynamics365.svg` |

### Icons in `docs/diagram/icons/` (embedded)

Get the style from `scripts/icon_style.py`. It runs the icon check, then prints the style
and the aspect-correct size. An SVG embeds as `image=data:image/svg+xml,<base64>`. A PNG
embeds as `image=data:image/png,<base64>`, also with no `;base64` marker: draw.io inserts
it when the cell loads.

Add one row per file in `docs/diagram/icons/`. Draw a wordmark wide (width about 110) and
a square mark at 48:

| File | For | Width |
|---|---|---|
| `clickhouse.svg` | ClickHouse | 24 inside a box, 48 alone |
| `docker.svg` | Docker | 24 inside a box, 48 alone |
| `kubernetes.svg` | Kubernetes | 24 inside a box, 48 alone |
| `minio.svg` | MinIO | 24 inside a box, 48 alone |
| `nginx.svg` | nginx | 24 inside a box, 48 alone |
| `opentelemetry.svg` | OpenTelemetry Collector | 24 inside a box, 48 alone |
| `postgresql.svg` | PostgreSQL | 24 inside a box, 48 alone |
| `redis.svg` | Redis | 24 inside a box, 48 alone |

A service that is none of these: see the skill's step 5.

## 4. Containers

Containers are ordinary vertices that other cells name as their `parent`. Add
`container=1;` so draw.io moves the children with them when someone edits the file.

AWS account (dark outline, AWS logo top-left):

```
shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;verticalAlign=top;align=left;grIconSize=30;spacingLeft=35;spacingTop=4;fillColor=none;strokeColor=#232F3E;fontColor=#232F3E;html=1;container=1;
```

VPC (green outline, VPC icon):

```
shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc;verticalAlign=top;align=left;grIconSize=30;spacingLeft=35;spacingTop=4;fontColor=#248814;strokeColor=#248814;fillColor=none;html=1;container=1;
```

Region (dashed blue): `grIcon=mxgraph.aws4.group_region;dashed=1;fontColor=#0E82B8;strokeColor=#0E82B8;`
with the same remaining entries. Security group: `grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#DD344C;fontColor=#DD344C;`.

Anything that is not AWS (GitHub, a SaaS workspace, a developer's machine) is a rounded
rectangle with the provider's colour as the stroke and a light tint of it as the fill,
and the provider's icon placed as a child in its top-left corner:

```
rounded=1;arcSize=4;whiteSpace=wrap;html=1;verticalAlign=top;align=left;spacingLeft=56;spacingTop=10;fillColor=#F0F7FF;strokeColor=#2088FF;fontColor=#1B3139;container=1;
```

(`#2088FF`/`#F0F7FF` for GitHub. With no icon, use `spacingLeft=10`; for a neutral
boundary with no provider, `#6B7280`/`#F9FAFB`.) The corner icon is 36×36 at `x=12`,
`y=8`; GitHub's is the built-in stencil `shape=mxgraph.weblogos.github;aspect=fixed;`.
An outside service that acts on the repository (a bot, a hosted app) gets its own
container beside the one it acts on, so its edges do not cut through another provider's
box.

## 5. Edges

```xml
<mxCell id="e-producer-msk" value="IAM auth" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;fontSize=10;labelBackgroundColor=#FFFFFF;" edge="1" parent="1" source="producer" target="msk">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

| Meaning | Style additions |
|---|---|
| Data flows (the default) | `strokeColor=#232F3E;strokeWidth=1.5;` |
| Control: a trigger, a start, a schedule | `dashed=1;strokeColor=#E7157B;` |
| Deployment or configuration | `dashed=1;dashPattern=1 3;strokeColor=#6B7280;` |
| Network path (peering, an endpoint) | `endArrow=none;strokeColor=#8C4FFF;strokeWidth=2;` |

Set `parent="1"` on an edge even when both ends sit in the same container. The label says
*over what* (IAM, JDBC, peering, OIDC) or *what* (the topic's name), never both.

Crossing edges are the most common defect. Place the vertices so the main flow is a
straight line, and add waypoints (`<Array as="points"><mxPoint x=".." y=".."/></Array>`
inside the geometry) only where the router cannot avoid a box.

## 6. Pitfalls

- **A style entry ends at `;`.** That is why an embedded icon is
  `image=data:image/svg+xml,<base64>` (or `image=data:image/png,<base64>`) with no
  `;base64` marker. `icon_style.py` does this for you.
- **No image linked by URL or file path.** `render.py` refuses any `image=` that is not
  a data URI or `img/lib/...`, because the next edit would depend on the network or on
  one machine's disk.
- **No compressed diagrams.** If you start from a file saved by the draw.io app,
  `render.py extract` returns the uncompressed model. `render.py export` records the
  model uncompressed too (`-u`), so a version diffs as text and its labels can be
  searched; `check_diagrams.py` refuses a compressed one.
- **Fonts are not embedded** in the recorded SVG (they tripled its size); viewers use
  their own sans-serif. Leave room in boxes for a slightly wider font.
- **A child's coordinates are relative to its parent.** An icon that renders outside its
  VPC usually has absolute coordinates under a container parent.
- **The export does not run layouts.** A `childLayout=stackLayout` container (a class, a
  table) arranges its rows when someone edits the file in draw.io, but the export uses the
  geometry written in the XML. Write each row's `y` and the container's full height.
- **`direction=` turns a shape's connection points with it.** On a shape with
  `direction=south`, `entryX=0` is no longer the left side. Leave `direction` off any
  shape an edge enters or leaves at a fixed point.
- **Two edges between the same two shapes overlap** unless each has its own
  `exitX`/`exitY` and `entryX`/`entryY`.
- **Headless Linux** needs `xvfb-run` in front of the draw.io CLI.
