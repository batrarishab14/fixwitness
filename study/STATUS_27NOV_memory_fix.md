# Status, 27 Nov (memory-runaway fix session)

Branch `claude/fixwitness-memory-leak-8ej3fi`, draft PR #2 into main. Not merged.

## Done and verified
- jira@v1.10.3 crash: every SQL case held a copy of every table (jira's comment.csv seed is 16.8 MB); fixed in
  `cases.py` / `sql.py`; regression test added; jira now PASS at ~783 MB peak. Full suite 128 passed, 19 skipped.
- `run_study.py --memory-gb` (default 8): an out-of-memory candidate is recorded "could not run", not a dead shard.
- `study.yml`: a run of named candidates saves to `study-results-only`, not over `study-results`.
- The six shard-5 candidates ran (run 46053580295, without the "not exercisable" check, so not comparable to the 110 rows):
  jira PASS, pendo PASS, zendesk@v0.18.1 PASS, fivetran_log@v2.1.0 and shopify_source@v0.15.0 "no compiled SQL changed",
  quickbooks@v0.5.1 FAIL (50 differences: `unique_id` replaced by `transaction_id` in quickbooks__general_ledger; the note
  mentions that index change but its bug is duplicate records, so UNCLEAR, not a confirmed catch). Results: branch `study-results-only`.
- Non-dbt case: benchmark/nondbt/openbb_yang_zhang (OpenBB PR #7807, a real pandas bug fix): FAIL on 170 of 208 inputs at window 2.
  Retrospective, not a new find. OpenBB formulas I read (Parkinson, Garman-Klass, Hodges-Tompkins, Sharpe, Sortino, Omega, skew,
  kurtosis) match their definitions: no bug found.

## Open
- CI on PR #2 head: `tests` and `data` were still running when this was written (last green: 723ae81).
- fixwitness limit found: cases vary only the first 3 rows, so rolling-window code with a window above ~2 is barely tested; and the
  report says "rows added or lost" when only values changed. Neither is fixed.
- Not merged, user decides: PR #2, exercise-check, exercise-synthesis, mutation-bench.
- User steps: Zendesk #284 PR, v0.6.0 release, PyPI publisher + `pypi` environment, GitHub Pages.
- Next idea: run fixwitness on recent refactor commits in widely used non-dbt products to find still-open bugs (user approves every PR).
