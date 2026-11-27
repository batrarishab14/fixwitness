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
