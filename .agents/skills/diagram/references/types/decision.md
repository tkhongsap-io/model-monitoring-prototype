# `decision`

Answers: **given a case, which outcome does it get, and by which questions?** Per
subject; the subject is the one decision (`refund-routing`, `plan-eligibility`).

A decision tree: questions, branches, outcomes, nothing else. Leaves out who decides and
what happens afterwards. If the picture needs steps over time or several actors it is the
`workflow`; if it explains why the project chose one design over another it is an ADR,
not a diagram.

Start `0001` from `assets/examples/decision.drawio`.

## Draw from

- As built: the function, rule set, policy file, or configuration that makes the
  decision. Each condition the code tests is a question, in the order the code tests it;
  each value returned or action taken is an outcome. Thresholds go in the question with
  their real value (`Amount over 500?`), read from the code or the configuration.
- Proposed: the spec, the policy document, or the conversation. Name each in
  `## Sources`.

A branch the code has and the policy document does not, or the reverse, is a finding:
report it, and draw what the code does.

## Shapes

| Element | Style | Size |
|---|---|---|
| Start: the case being decided | `rounded=1;arcSize=50;whiteSpace=wrap;html=1;fontSize=11;fillColor=#232F3E;strokeColor=#232F3E;fontColor=#FFFFFF;` | 140×40 |
| Question | `rhombus;whiteSpace=wrap;html=1;fontSize=11;fillColor=#FFFFFF;strokeColor=#232F3E;fontColor=#232F3E;` | 180×90 |
| Outcome | `rounded=1;whiteSpace=wrap;html=1;fontSize=11;fillColor=#F0F7FF;strokeColor=#2088FF;fontColor=#232F3E;` | 170×50 |

Branch, labelled with the answer (`yes`, `no`, or the value: `gold`, `over 30 days`):

```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;fontSize=10;strokeColor=#232F3E;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;
```

A question is a question, ending in `?`, answerable from the case alone. An outcome says
what the case gets, in the words the code or the policy uses.

## Layout

- Top to bottom. Questions in one column, 140 px between their tops, in the order they
  are asked.
- The answer that ends the decision leaves to the right, to an outcome level with its
  question. The answer that continues goes down to the next question. Keep the same
  answer on the same side where the logic allows; where it does not, the labels carry it.
- The last question's remaining answer goes down to its outcome.
- A question with three or more answers fans out to the right, one outcome under another.
- More than about eight questions: the decision has a sub-decision. Give it its own
  subject and end this branch at an outcome that names it.

## A new version when

A question, a branch, or an outcome is added, removed, or reordered, or a threshold in a
question changes. Not for a reworded label that asks the same thing.

## Check the preview

Every question has a labelled branch for each answer; every path ends at an outcome; no
branch crosses another.
