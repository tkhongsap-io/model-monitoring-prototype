# Use-case template: task type and output (one for each GCP use case)

| | |
|---|---|
| **Status** | Draft 2026-10-08 |
| **Who answers** | The GCP job developer of each use case, with the use-case owner |
| **Where** | One comment for each use case on the S1-09 issue. Copy the form below. |
| **Why** | The answers select the quality profile and the metrics of the use case ([core-metrics.md](core-metrics.md)). |

**Rules for the answers**
- Write the structure only. Do not write real prompts, real outputs, customer data, keys or
  URLs.
- If you do not know an answer, write `unknown` and the name of the person who knows.
- For a field list, write the names and the types, for example `label: string`.

## Form (copy one for each use case)

```markdown
### Use case: <use_case_id> — <short name>

**A. Job**
| # | Question | Answer |
|---|---|---|
| A1 | Owner of the use case (name, team) | |
| A2 | Job developer (name) | |
| A3 | Schedule (for example daily 02:00 UTC, weekly Monday) | |
| A4 | Approximate requests in one run | |
| A5 | Gemini mode: Batch API, or online calls | |
| A6 | Usual time from batch submit to results published (for example 2 h) | |
| A7 | Gemini model ID | |

**B. Input of one request**
| # | Question | Answer |
|---|---|---|
| B1 | Input types: text / document text / image / PDF / audio / other | |
| B2 | Number of images or files in one request (0 if none) | |
| B3 | Is there per-request text input (for example a document, a transaction, a complaint)? What is it? | |
| B4 | Is the instruction the same for all requests (a fixed prompt)? | |
| B5 | Language of the text: Thai / English / mixed / none | |
| B6 | Can the input contain PII? Which types (phone, email, national ID, name, address, account, other)? | |

**C. Output of one request**
| # | Question | Answer |
|---|---|---|
| C1 | Output type: one label / several labels / structured fields / free text / mix | |
| C2 | Is the output JSON with a fixed format? | |
| C3 | Field names and types (no values) | |
| C4 | If a label: the list of all possible labels | |
| C5 | Is there a confidence or score field? Name and range (for example 0 to 1) | |
| C6 | Free-text fields in the output (for example "reason", "summary"). Their names. | |
| C7 | Can the output contain PII? In which fields? | |
| C8 | How does the job detect a refusal or a safety block? | |

**D. Correct answers (for accuracy later)**
| # | Question | Answer |
|---|---|---|
| D1 | Does a correct answer become known later (for example a confirmed fraud case, a corrected field)? | |
| D2 | If yes: where is it stored, who owns it, and how long after the run does it arrive? | |
| D3 | Can it be matched to one request (by `record_id` or another request ID that is not a customer ID)? | |
| D4 | Can a person review a small sample (for example 20 records each week)? Who? | |

**E. Use of the output**
| # | Question | Answer |
|---|---|---|
| E1 | What does the business do with the output (for example block a payment, send to an investigator, send a letter)? | |
| E2 | Does a person check the output before an action? | |
```

## Example: the fraud validation job (partly known)

From the first two bodies (2026-10-07) and the GCP answers on #3 (2026-10-08). The
developer completes it on the S1-09 issue.

| # | Answer |
|---|---|
| A4 | About 112 to 243 requests in one run |
| A5 | **Online** calls. `latency_s` is the time of each SDK call, measured in the job. |
| A7 | `gemini-2.5-flash` |
| B1 | Images + a fixed prompt |
| B2 | 3 |
| B3 | No |
| B4 | Yes. The system prompt is about 9,600 characters and is not sent. `question` is `Process These Images [IMAGE] [IMAGE] [IMAGE]`. |
| C1 | Structured result: three check results in the form `x/3` and four sub-counts (not one label) |
| C2 | Yes, fixed JSON |
| C3 | The developer gives the field names on the S1-09 issue |
| D1 | To ask: are fraud cases confirmed later? |

## How the answers select the profile

| B and C answers | Profile |
|---|---|
| C1 = one label or several labels | `classification` |
| C1 = structured fields | `extraction` |
| C1 = free text, and B3 = yes (a text source) | `generation_from_text` |
| C1 = free text, and B3 = no | `generation_free` |
| C1 = mix | The profile of the main output. The free-text fields get `pii_exposure_rate` (C6). |

RAI confirms the profile of each use case. The registry (S2-01) records it.

## Summary table (backend fills it from the answers)

| Use case | Owner | Mode | Input | Output | Profile | Text source | Free-text output | Confidence | Labels later | Reviewer |
|---|---|---|---|---|---|---|---|---|---|---|
| Fraud validation (`rtr-fraud-validation`) | ? | Online | 3 images | Fixed JSON: 3 checks (`x/3`) + 4 sub-counts | `extraction` or `classification` (RAI decides) | No | ? | ? | ? | ? |
| UC-02 | | | | | | | | | | |
| UC-03 | | | | | | | | | | |
| UC-04 | | | | | | | | | | |
| UC-05 | | | | | | | | | | |
| UC-06 | | | | | | | | | | |
| UC-07 | | | | | | | | | | |
| UC-08 | | | | | | | | | | |
| UC-09 | | | | | | | | | | |
| UC-10 | | | | | | | | | | |
