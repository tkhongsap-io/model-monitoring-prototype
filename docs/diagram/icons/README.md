# Icons

These are provider icons downloaded for the diagrams, because draw.io's built-in
libraries do not have them. Each one is embedded in a diagram as a data URI, so no diagram
depends on this directory to render. The files are kept so the next version can embed
them again, and so their origin and license are on record.

Each file is an SVG or a PNG that `fetch_icon.py` downloaded and the icon check accepted.
It is kept byte for byte as downloaded, with two exceptions: an SVG ends in exactly one
newline, and a Simple Icons SVG may get its brand colour from `data/simple-icons.json` as
`fill`. A file that fails the icon check is refused, never repaired. Rule and source
order: [`.agents/rules/diagram.md`](../../../.agents/rules/diagram.md#icons).

Each row records:

- **License / terms:** the license name, linked to the page that grants it.
- **Credit:** the attribution the license asks for, or `—`.
- **SHA-256:** the hash of the committed file. The check fails when the file changes
  without its row.

A brand's mark stays its owner's trademark even when the file is CC0 (Simple Icons). Note
any brand guidelines in the License / terms cell.

| File | For | Source | License / terms | Credit | Retrieved | SHA-256 |
|---|---|---|---|---|---|---|
