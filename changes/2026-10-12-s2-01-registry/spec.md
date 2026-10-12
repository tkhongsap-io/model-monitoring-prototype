# Spec: source registry of the batch use cases (S2-01)

Intent and decisions: `intent.md` in this folder.

## Files

| File | Change |
|---|---|
| `backend/registry/batch-use-cases.yaml` | New. The registry (one entry: `rtr-fraud-validation`) |
| `backend/app/registry.py` | New. Models, loader, the current registry, readiness helper |
| `backend/app/config.py` | New setting `BATCH_REGISTRY_PATH` |
| `backend/app/main.py` | The lifespan loads the registry before the database |
| `backend/app/api/batch_routes.py` | `403` for a key of an unregistered use case |
| `backend/app/api/ops_routes.py` | Readiness reports key entries of unregistered use cases |
| `backend/scripts/batch_keys.py` | New. `make`, `add`, `list`, `remove` |
| `backend/tests/fixtures/batch-use-cases.test.yaml` | New. Test registry: `GCP-UC-03`, `GCP-UC-07` |
| `backend/tests/test_registry.py`, `backend/tests/test_batch_keys.py` | New tests |
| `backend/tests/conftest.py` | All tests use the test registry by default |
| `backend/tests/test_batch_runs_api.py`, `backend/tests/test_compose_files.py` | Changed and new tests |
| `deploy/compose/compose.local.yaml`, `scripts/compose-smoke.sh` | Local key mapped to `rtr-fraud-validation` |
| `issues.md` (S2-01), `docs/STRICT-LIVE.md` ("Batch run receiver"), `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md` | Docs |

No new package (PyYAML and Pydantic are installed). No database migration.

## The registry file

`backend/registry/batch-use-cases.yaml`:

```yaml
# Batch use cases of the October MVP (S2-01). A change is a pull request, approved by
# backend; RAI also approves band_overrides. Never put an API key or a key hash here:
# the hashes are in BATCH_API_KEY_SHA256 of the host env file (scripts/batch_keys.py).
use_cases:
  - use_case_id: rtr-fraud-validation
    name: RTR fraud validation
    owner: RTR fraud team
    developer: Prakasit Issanapong
    mode: identity_only
    schedule:
      expected_every_s: 86400
      grace_s: 21600
    turnaround_limit_s: null
    data_classification: confidential
    band_overrides: {}
```

`turnaround_limit_s: null` means "not set": `turnaround_s` is Unknown with `not_reported`
until RAI sets a limit (core metrics). `owner` is the owner team name from S1-09.

## `app/registry.py`

```python
class Schedule(BaseModel):            # extra="forbid"
    expected_every_s: int             # > 0
    grace_s: int                      # >= 0

class UseCase(BaseModel):             # extra="forbid"
    use_case_id: ID                   # the same type as batch_schema (max 128, pattern)
    name: str                         # 1..128
    owner: str                        # 1..128
    developer: str                    # 1..128
    mode: Literal["identity_only", "records"]
    schedule: Schedule
    turnaround_limit_s: int | None    # > 0 when set
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    band_overrides: dict[str, dict[str, float]] = {}

class Registry(BaseModel):            # extra="forbid"
    use_cases: list[UseCase]          # at least 1, unique use_case_id

class RegistryError(Exception): ...   # message names the file, the entry and the field

def load(path: str | Path) -> dict[str, UseCase]     # raises RegistryError
def current() -> dict[str, UseCase]                  # the loaded registry; RegistryError if not loaded
def set_current(registry: dict[str, UseCase]) -> None
def unregistered(use_case_ids: Iterable[str], registry: dict[str, UseCase]) -> list[str]  # sorted, unique
```

Rules of `load`:
- The file must exist and parse as YAML, else `RegistryError("batch registry <path>: <reason>")`.
- Pydantic errors become one line for each error:
  `batch registry <path>: use case <id or #position>: <field.path>: <message>`.
  `#position` counts from 1 and is used when the entry has no valid `use_case_id`.
- A duplicate `use_case_id`: `batch registry <path>: use case <id>: duplicate use_case_id`.
- An empty list or an empty file is an error.
- Fields of after October (`task_description`, `profile`, `sample_size`) are unknown fields
  and fail like any other unknown field.

## Settings and start

`config.BATCH_REGISTRY_PATH`: environment variable `BATCH_REGISTRY_PATH`, default the
absolute path of `backend/registry/batch-use-cases.yaml` (from `Path(__file__)`).

`main.lifespan`: first `registry.set_current(registry.load(config.BATCH_REGISTRY_PATH))`,
then `db.engine()`. A `RegistryError` is not caught: the app does not start, and uvicorn
prints the error and exits with a non-zero code. The docstring of `main.py` says this.

## Key check (`batch_routes._ingest`)

After `_use_case_of_key` returns a use case (else `401` as today):
- If that use case is not in `registry.current()`: `403`, body
  `{"detail": "the use case of this API key is not registered"}`, span attribute
  `outcome=unregistered`, warning log with `key_use_case_id`. This check comes **before**
  the body is read.
- The existing check "the body's use case equals the key's use case" (`403`) does not change.

## Readiness (`ops_routes.readiness`)

Add, for the key entries of `config.batch_api_key_hashes()`:
`registry.unregistered(ids, registry.current())`. If not empty, add the error
`"BATCH_API_KEY_SHA256 has entries for use cases that are not in the registry: <ids>"`.
The use case IDs are not secret; the hashes are never shown. Readiness also shows
`"use_cases": <number of registered use cases>`.

## `scripts/batch_keys.py`

Standard library only (`argparse`, `secrets`, `hashlib`, `os`, `re`, `tempfile`, `sys`).
`#!/usr/bin/env python3`. Exit `0` on success, `1` on a refused action, `2` on a usage error.

| Command | Behaviour |
|---|---|
| `make --use-case ID --key-out PATH --hash-out PATH` | `ID` must match the `use_case_id` pattern. Refuses if an output file exists. Key = `secrets.token_urlsafe(32)`. Writes the key (no newline) and the line `ID:<sha256 hex>` with `os.open(..., O_CREAT \| O_EXCL \| O_WRONLY, 0o600)`. Prints `wrote key to <path> and hash line to <path>` only. |
| `add --env-file PATH --hash-file PATH` | Reads one `ID:<64 hex>` line from the hash file (else refuse). In the env file, finds the line `BATCH_API_KEY_SHA256=...` (adds it if absent). Refuses if the same hash is already there. Appends `, ID:<hash>` (or sets it if empty). Writes a temporary file in the same folder with mode 600 and `os.replace`s it; keeps every other line and keeps the original file mode. Deletes the hash file. Prints `added a key for ID (<hash[:8]>)`. |
| `list --env-file PATH` | One line for each entry: `<use_case_id> <hash[:8]>`. A malformed entry: `#<position> malformed`. |
| `remove --env-file PATH --use-case ID --hash-prefix PREFIX` | `PREFIX`: 8 to 64 hex characters. Refuses unless exactly one entry has that use case and a hash that starts with the prefix. Removes it with the same safe write. Prints `removed a key for ID (<prefix[:8]>)`. |

No output line contains a key or more than 8 characters of a hash. The env file format is
the one of `backend.env` (`NAME=value`, `#` comments); values are not quoted.

## Local stack and smoke test

- `compose.local.yaml` backend: `BATCH_API_KEY_SHA256: rtr-fraud-validation:ca9263478834f0d9f054e84eda1a55dee86d8a6551f27aa8a2c751a4b541b200`
  (the hash of the same local test key).
- `scripts/compose-smoke.sh`: the Python block that writes `body.json` also sets
  `body["use_case_id"] = "rtr-fraud-validation"`.
- `test_compose_files.py`: `test_local_file_builds_backend_and_waits_for_postgres` expects
  `rtr-fraud-validation:<hash>`; the smoke-script test checks the `use_case_id` line.

## Tests

`backend/tests/conftest.py`: an autouse fixture sets `config.BATCH_REGISTRY_PATH` to
`tests/fixtures/batch-use-cases.test.yaml` (entries `GCP-UC-03` and `GCP-UC-07`, the use
cases of the S1-01 examples) and calls `registry.set_current(registry.load(...))`, so tests
that call routes without the lifespan also have a registry. A test that needs the real
file loads it explicitly.

`test_registry.py`:
- the real file loads and contains exactly `rtr-fraud-validation`, `identity_only`;
- the real file has no `task_description`, `profile`, `sample_size`, and no text that looks
  like a key hash (`[0-9a-f]{64}`);
- each bad file fails with the expected words in the message: duplicate ID; ID with a space;
  unknown field `task_description`; `mode: other`; `expected_every_s: 0`; `turnaround_limit_s: 0`;
  `grace_s: -1`; empty file; `use_cases: []`; YAML that does not parse; a file that does not exist;
- the app does not start: with `BATCH_REGISTRY_PATH` set to a bad file, `with TestClient(main.app)`
  raises `RegistryError`;
- `unregistered` returns the sorted unique unknown IDs.

`test_batch_runs_api.py` (new or changed):
- a key for an unregistered use case (`GCP-UC-99:<hash>` in the env, not in the test registry) → `403` "not registered", and no row;
- key A with a body for B (both registered) → `403` (exists; keep);
- a removed key → `401`;
- rotation: two keys for `GCP-UC-03` both give `201`/`200`; after one is removed from the
  setting, it gives `401` and the other still works; the stored rows do not change;
- readiness with `GCP-UC-99` in the setting → `503` with the "not in the registry" error,
  and the response contains no hash.

`test_batch_keys.py` (temporary folder; the script is run with `subprocess` and
`sys.executable`):
- `make` writes two files; on POSIX their mode is `0o600` (skip the mode check on Windows);
  the output contains neither the key nor the full hash; the hash line matches the key;
  `make` refuses an existing output file and a bad ID;
- `add` keeps the other lines and comments, refuses a duplicate, deletes the hash file, and
  the result passes `config`'s parser (`_batch_key_entries` equivalent: parse the value with
  the same split rule and check each entry);
- `list` prints `<id> <8 hex>` lines only;
- `remove` refuses prefixes that match 0 or 2 entries and a prefix shorter than 8; removes
  exactly one entry otherwise.

CI: the smoke test passes with the local key mapped to `rtr-fraud-validation`.

## Docs

- `issues.md` S2-01: a dated note at the top (decision B; October fields; design folder).
  In the "Part" table, the API key row location becomes "the backend env file
  (`BATCH_API_KEY_SHA256`)".
- `docs/STRICT-LIVE.md`, "Batch run receiver": the registry file and the new `403`.
- `deploy/compose/TESTHOST.md`: a section "Add or rotate an API key (S2-01)" with the
  laptop and VM commands of `batch_keys.py`, then the backend restart.
- `CHANGELOG.md` and `DEVLOG.md`.

## Not in scope

The other 6 use cases (S2-06), the task description, the profile and the sample size
(after October), a database table for the keys, and using the schedule and the limits
(S2-05, S3-02).
