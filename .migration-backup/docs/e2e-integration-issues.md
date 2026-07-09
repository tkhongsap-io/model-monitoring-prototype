# E2E Integration Issue Log

Date: 2026-07-08 (Asia/Bangkok)

Scope: backend + frontend local run, in-app browser E2E checks, build/tests.

## Issues Found And Resolved

| ID | Issue | Evidence | Resolution | Status |
|---|---|---|---|---|
| E2E-001 | Windows `npm install` failed when run directly from the raw WSL UNC path. | `CMD.EXE` defaulted to `C:\Windows`; `unrs-resolver` postinstall could not find `postinstall.js`. | Installed frontend dependencies from inside WSL with a user-local Node runtime. | Closed |
| E2E-002 | Windows Next dev server against the mapped WSL path did not serve reliably. | Repeated Watchpack `EISDIR` watcher errors and HTTP timeout on `http://localhost:3000`. | Ran Next dev from WSL so the runtime and watched filesystem match. | Closed |
| E2E-003 | Linux frontend launch initially failed after Windows-created `node_modules`. | `sh: 1: next: Permission denied`; `node_modules/next/dist/bin/next` was `0644`. | Removed generated `node_modules`/`.next` and reinstalled with WSL npm; `next` became executable. | Closed |
| E2E-004 | Running `next build` while the dev server was using the same `.next` cache caused a transient blank page. | Browser showed blank UI with `TypeError: __webpack_modules__[moduleId] is not a function`; server returned `GET / 500`. | Stopped Next before build; after build, cleared `.next` before restarting dev. | Closed |
| E2E-005 | Frontend build emitted a React hook dependency warning in Portfolio. | `npm run build` warned that `all` could change on every render in `src/app/portfolio/page.tsx`. | Added a stable `EMPTY_ROWS` fallback for `data?.rows`. | Closed |
| E2E-006 | Browser E2E emitted a React key warning in Action Queue. | Fresh browser console error: each child in a list should have a unique `key` prop in `Actions`. | Wrapped each mapped action row pair in a keyed `Fragment`. | Closed |

## Final Verification

| Check | Result |
|---|---|
| Demo bake | `scripts/demo_reset.py` completed 20 ticks for `DEMO-FULL`, seed 42. |
| Backend tests | `backend/.venv/bin/python -m pytest tests` passed `20 passed`. |
| Frontend build | `npm run build` passed with no warnings after fixes. |
| Backend endpoint | `GET http://localhost:8000/api/health` returned `{"ok": true}`. |
| Next rewrite | `GET http://localhost:3000/api/summary` returned the expected 130-row seeded portfolio summary. |
| In-app browser route checks | `/`, `/portfolio`, `/pilot`, `/heatmap`, `/gaps`, `/actions`, `/board`, `/use-case/AICT-P01`, and `/use-case/AICT-P02` all rendered expected hydrated content. |
| Scenario player E2E | `+1`, jump to tick 14, Action Queue red-state check, and reset to tick 0 all passed. |
| Browser console | Final fresh in-app browser pass had no new console errors. |

## Notes

- The frontend is displayed in the in-app browser at `http://localhost:3000`.
- Backend remains on `http://localhost:8000`; frontend remains on `http://localhost:3000`.
- A Next dev dependency warning about `util._extend` can appear under Node 24. It did not appear as a browser error or build failure.
