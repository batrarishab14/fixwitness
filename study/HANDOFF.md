# fixwitness handoff (self-contained; updated 27 Nov 2026 02:40 ET)

New session: attach batrarishab14/fixwitness with push access, read this file, then continue at "Next".
Rules: verify every number; separate verified from inferred; commits as Rishab Batra <batrarishab14@gmail.com> with
the Co-Authored-By trailer of the active model; no Morgan Stanley material; no PRs on others' repos without go-ahead;
commit/push continuously and append here after every step.

## State (verified)
- main = b5945cb (PR #1 merged as 040cc09; skill at .claude/skills/fixwitness-check/; CI green).
- Branch `exercise-check` (commit 3eb08e4 + a later docs/scripts commit): plan item 1, "not exercisable with this
  data" (src/fixwitness/exercise.py). Local suite 155 passed, 16 skipped (DuckDB not installed in the sandbox).
  CI `tests` green; `data` was still running at the last check. NOT merged: merge only after `data` is green and the
  user agrees.
- Real-data check, dbt_quickbooks, seeds only: see benchmark/realrepo/exercise_validation/README.md.

- Branch `exercise-synthesis` (on top of exercise-check): item 2 phase 1. When the check finds a value the change tests
  that no input has, up to 12 `precondition` cases give that value to the column it is compared with (SQL mode,
  honouring dbt contracts), so the change gets a row to run on. Local suite 156 passed, 16 skipped. Demonstrated in
  tests on SQLite only (silent PASS with the check off, FAIL with it on). NOT yet run on real dbt projects or the study.
  Not covered yet: values hidden in functions (`coalesce(col, '') <> 'x'`), non-text columns, multi-table
  preconditions (a second linked row, a true flag on that row), null-only numeric columns.

- STUDY RUN launched 27 Nov 03:07 ET on branch exercise-synthesis (commit 0373f71): workflow `study`, run id
  45962989074, https://github.com/batrarishab14/fixwitness/actions/runs/45962989074 . Results go to the
  `study-results` branch (results.csv). Compare with run5 (benchmark/realrepo/runs/run5/results.csv): catch rate AND
  false alarms (refactors and bug fixes that now say INCONCLUSIVE or FAIL). Do not quote numbers before hand-reading
  the new INCONCLUSIVE/FAIL rows. Nothing merged to main; merge only on user go-ahead after CI is green.

## Known caveats
- Not measured: other packages, the full-case run, the 63-candidate catch rate and false-alarm rate (that is item 2).
- Not detected by design: join multiplicity, broken foreign keys, rows that never repeat. Silence is not a claim.
- v0.9.1 flagged on `credit` is probably a seeds-only artifact; confirm with a real CI run.
- Git-install fallback of the skill is untested on a normal-network machine.

## Next (in order)
1. Check CI `data` on exercise-check; if green and the user agrees, merge to main. If red, diagnose first.
2. Generic seed synthesis (keep FKs/constraints, add missing precondition rows); re-run the 63-candidate study;
   report the new catch rate AND false alarms (this also measures the new check at scale).
3. PR/CI GitHub Action that comments what a data-code change altered.
4. Non-dbt real-bug study (SQL, pandas, PySpark).
5. More live-package bugs with fix PRs + proof (go-ahead needed).
6. Evidence log of outside-verifiable items.
