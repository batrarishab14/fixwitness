# FIXWITNESS HANDOFF FOR THE NEXT AI (written 27 Nov 2026, ~19:40 UTC)

Self-contained: read this whole file, then continue from "NEXT STEPS". Everything below was checked against git/GitHub/CI in
the session that wrote it, unless marked INFERRED or UNVERIFIED. If you cannot verify something, say so; never round up.

## 1. What this is and why it matters
fixwitness (github.com/batrarishab14/fixwitness, the user's own repo, MIT) checks a change to SQL / dbt / pandas / PySpark code:
it runs the original and the changed code on ~300 generated edge-case inputs and reports where the output differs. No expected
output is needed. Pitch: "See what your code change does to the numbers before it ships."
The user's real goal: outside-verifiable recognition (EB-1A evidence) by solving real problems: merged fixes in widely used
products, real users, a paper. Judge every piece of work by: solves a real problem, easy to adopt, reliable, verifiable.
Honest state: ZERO outside users, one ready-but-unsubmitted outside fix (Zendesk #284). Hardening work is not evidence by itself.

## 2. Rules from the user (follow strictly)
- Verify every number before reporting it; separate VERIFIED from INFERRED. Never assume.
- Commits authored as `Rishab Batra <batrarishab14@gmail.com>`; trailer `Co-Authored-By:` naming YOUR model. No Morgan Stanley material anywhere.
- Never open a PR / issue / comment on someone else's repo without explicit go-ahead. Never merge any branch unless the user says so.
- Save continuously (commit + push) and update a status file after every step.
- One item at a time, in order. The user reads on a phone and wants short answers, ETAs when asked, and plain English.
- The user is near a weekly usage limit (warning, not blocked; resets Thu 3 Dec 20:00 UTC). Prefer cheap steps; do not poll CI.

## 3. Repo and branch state (VERIFIED 27 Nov)
- `main` HEAD b5945cb, CI green. Contains fixwitness 0.6 (PR #1 merged) and the Claude Skill at `.claude/skills/fixwitness-check/SKILL.md`.
- `claude/fixwitness-memory-leak-8ej3fi` = DRAFT PR #2 into main (head 4e77fb3, docs-only on top of ddeec08). Memory-runaway fix. See section 4.
  CI: last fully green commit 723ae81 (tests + data, push + PR). Checks on ddeec08 were still running at hand-off (`data` takes ~90 min). Check them first.
- Unmerged, all CI green when last checked, user decides on merging: `exercise-check` ("not exercisable with this data" check instead of a silent PASS),
  `exercise-synthesis` (includes exercise-check; adds value synthesis + a CI job `install-from-github`), `mutation-bench`
  (27 mutants from 6 author-written SQL queries on SQLite; fixwitness caught 18/18 non-equivalent; SMALL sample, author-written).
  PR #2 merges cleanly into mutation-bench; into exercise-synthesis only `study/DEVLOG_v0.6.md` conflicts (both append to it).
- Other branches: `study-results` (110 rows of the exercise-synthesis study run; force-pushed by every full study run), `study-results-only`
  (NEW: the six shard-5 candidates), `diag-tmp` (throwaway diagnostics, never merge), `dev-0.6` (merged).

## 4. This session's main result: memory runaway FIXED (VERIFIED)
Study shard 5 killed its runner on every run. Cause: every SQL case stored a JSON bundle of ALL input tables, built before the 300-case cap;
dbt_jira's comment.csv seed is 16.8 MB, so fixwitness passed 5 GB. A user project with one big seed would hit this too.
Fix: `Case.content` may be a function (`cases._Content`); SQL cases share one tables dict (`sql.lazy_bundle`). jira@v1.10.3 now finishes:
PASS, peak ~783 MB, 288 valid inputs, 0 changed (234 marked "unstable": the original's own output varied between runs; NOT investigated).
Regression test `test_cases_do_not_each_hold_every_table` fails on old code (176 MB for 90 cases) and passes now. Full suite: 128 passed, 19 skipped.
Guard: `benchmark/realrepo/run_study.py --memory-gb` (default 8) records an out-of-memory candidate as "could not run" instead of killing the shard.
`study.yml`: a run with `only=...` now saves to `study-results-only`, not over `study-results`.
Benchmarks: run_sql_bench and run_complex_bench give IDENTICAL results on main's code and on PR #2 (14 complex cases ran; pandas/polars/pyarrow cases
skipped locally for lack of libraries). The committed benchmark result files are out of date vs main itself (they predate the `pairs` category); not regenerated.

## 5. Study facts (VERIFIED unless marked)
- Run 5 (Fivetran dbt packages): bug fixes 63 of 71 checked; 31 flagged (49%, upper bound); hand-read against release notes: 22 confirmed (35%), 3 same model
  field not named, 4 unclear, 2 not the bug; 32 missed; 8 not checked. Refactors: 25 of 39 checked, 2 flagged, both real, 14 not checked. Files: benchmark/realrepo/runs/run5/.
- 9 of 9 checked misses share one cause: the package's own integration-test seed data lacks the row combination the bug needs (e.g. zero "Accounts Payable"
  rows). Not a fixwitness generation gap. 22 of the 32 misses are still undiagnosed. (lever-43, fivetran_log@v0.6.4, quickbooks@v0.5.3/v0.9.1/v1.6.2/v1.9.2, zendesk@v0.8.1/v1.0.1/v1.5.1.)
- Study with exercise-synthesis (run 45962989074, 110 rows): bug FAIL 31->32 (new: quickbooks@v0.5.3, matches hand diagnosis; NOT yet hand-read), 9 silent PASSes became
  "not exercisable". Refactor FAIL stayed 2 (no new false alarms). Do NOT quote a new catch rate until hand-read.
- Six shard-5 candidates, run 46053580295 on PR #2's branch (no "not exercisable" check, so NOT comparable to the 110): jira@v1.10.3 PASS, pendo@v1.4.0 PASS,
  zendesk@v0.18.1 PASS, fivetran_log@v2.1.0 and shopify_source@v0.15.0 "no compiled SQL changed", quickbooks@v0.5.1 FAIL (50 differences; `unique_id` replaced by
  `transaction_id` in quickbooks__general_ledger; the release note mentions that index change but its stated bug is duplicate records) = UNCLEAR, not a confirmed catch.
- Non-dbt: SQLMesh/Dagster history has almost no usable SQL bug-fix pairs. OpenBB PR #7807 (commit c6d097b27, Yang-Zhang volatility counted overnight variance twice) is a real
  pandas fix: `benchmark/nondbt/openbb_yang_zhang/` (build.py rebuilds it from an OpenBB clone; OpenBB is Apache-2.0; code deliberately not copied). fixwitness FAIL on 170 of 208 inputs at
  window 2. RETROSPECTIVE: someone else already fixed it; not a new find. I also read OpenBB's Parkinson, Garman-Klass, Hodges-Tompkins, Sharpe, Sortino, Omega, skew, kurtosis: they match their definitions, no bug found.
- Competitors: Datafold data-diff archived May 2024; Recce (dbt PR validation, Apache-2.0, ~484 stars).

## 6. Known fixwitness weaknesses (VERIFIED, not yet fixed)
1. [PARTLY FIXED 27 Nov, PR #2: CSV script mode only, `core._widen`; verified on the OpenBB case at window 30: 207 of 208 inputs; suite 139 passed, 10 skipped (pandas installed, so more ran than before). NOT fixed for SQL/JSON/Parquet/DataFrame-function mode.] Cases vary only the FIRST 3 ROWS. Rolling-window code (default window 30, most finance/time-series code) gets almost no useful cases: at window 5, 1 of 208 inputs showed the change; at window 2, 170.
   Fix idea: use more rows when the code needs them, and report "not enough rows to exercise this" instead of PASS.
2. Report wording says "rows added or lost" when only values changed.
3. Skill install fallback `pip install git+https://github.com/batrarishab14/fixwitness.git` is UNVERIFIED on a normal-network machine (the sandbox cannot reach PyPI for build deps; CI job `install-from-github` on exercise-synthesis tests it in a clean venv).
4. The "unstable" outputs on jira (234 of 288) are unexplained.

## 7. Environment notes and traps learned
- Sandbox: no `gh` for most things but `gh run`/`gh api` worked; `git push -u origin <branch>` works. hub.getdbt.com is BLOCKED, so `dbt deps` fails locally: use a shim that copies fivetran_utils 0.4.14, spark_utils 0.3.5, dbt_utils 1.3.3
  from GitHub and writes a package-lock.yml (see how it was done in the git history of this session's notes; CI uses real `dbt deps`). Local reproduction needs Postgres 16 (`service postgresql start`, user ci/ci, db test) and
  `FIXWITNESS_STUDY_WAREHOUSE=postgres://ci@localhost:5432/test`. Study = Postgres, NOT DuckDB: testing a package with plain DuckDB gives misleading crashes (an earlier session wasted time on this).
- CI has `concurrency: cancel-in-progress`: pushing a new commit cancels the 90-minute `data` run of the previous one. Use `[skip ci]` in docs-only commits.
- Every full study run force-pushes `study-results` (an `only=` run on this branch now writes `study-results-only`). Study artifacts cannot be downloaded from the sandbox; use the `collect` job's branch instead.
- Comparing "main vs branch" in a benchmark: use `git worktree` plus `PYTHONPATH=<worktree>/src`, because fixwitness is installed editable; a plain `cd` runs the wrong code (this caught one invalid run).
- A GitHub event's `head_sha` can be an older commit; check the current head before concluding anything.
- A quoted licence must be checked, not assumed (an AGPL claim about OpenBB was wrong; it is Apache-2.0).

## 8. NEXT STEPS (in order; do one at a time, report each)
1. Check CI on PR #2's head (tests + data). If green, tell the user it is ready; DO NOT merge.
2. Hand-read the new quickbooks@v0.5.3 FAIL (exercise-synthesis study) and quickbooks@v0.5.1 against their release notes; update counts only if verified.
3. Fix weakness 1 (rolling-window / row budget) and 2 on a new branch with a regression test; re-run the OpenBB Yang-Zhang case at window 30 to prove it.
4. Find still-open bugs: run fixwitness on recent refactor commits in widely used non-dbt products (candidates to fit-check, none verified to have bugs: Umami, Lago (Rails, ClickHouse not supported), OpenBB, Metabase/Superset/Lightdash).
   Goal 3-5 merged fixes. The user approves every PR.
5. Adoption (Phase 1): browser playground on GitHub Pages (Pyodide), GitHub Marketplace Action PR comment, pre-commit hook, MCP registry listing. `fixwitness check` with no args already checks the whole git change; `fixwitness doctor`, `fixwitness ui` and MCP-registry publishing on release already exist: do NOT rebuild them.
6. USER-ONLY steps (remind, never do): submit Zendesk #284 PR from the fork batrarishab14/dbt_zendesk branch `fix-unreplied-ticket-count` (commit b29ef3e; text in benchmark/realrepo/open_issues/zendesk-284/PR.md); create release v0.6.0; add PyPI pending publisher (project `fixwitness`, workflow `publish.yml`, environment `pypi`); create GitHub environment `pypi`; enable Pages (main, /docs); decide merges of PR #2, exercise-check, exercise-synthesis, mutation-bench.
7. Later: arXiv/IST paper, one article (validate venue first), talks, launch with ONE real story ("ran it on N products, found X wrong-number bugs, Y merged"): Show HN, r/dataengineering, dbt Slack.
8. After every step append to study/STATUS_*.md (or this file) and push.

## 9. Open question the user has not answered
Whether to start with step 4 (find still-open bugs in popular non-dbt products) or step 3 (fix the rolling-window limit). My recommendation: step 3 first (small, makes finance/time-series results trustworthy), then step 4.
