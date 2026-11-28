# fixwitness: CTO / solution-architect review (28 Nov 2026)

Written from the code on `main` (c3dcd2c, 9.5k lines in `src/fixwitness`, 174 tests), the study data and this week's
benchmark runs. VERIFIED means checked in the repo or a run; INFERRED means judgement.

## 1. Verdict in one paragraph
The engine is real and unusually careful (shrinking, replayable proofs, honest reasons). The product is not yet:
it tries to be three tools (a security-fix witness, a self-healing-repair witness and a data-change diff), its
evidence exists only for the third, its default inputs are tuned for the first, and nobody outside uses it.
The fastest path to both business value and EB-1A-grade evidence is to **narrow to one job, fix the noise and the
missing-precondition problem, and turn the study into a public benchmark and a paper**.

## 2. Scorecard (now -> realistic 90-day target)
| Area | Now | Target | Evidence for "now" |
|---|---|---|---|
| Business problem solved | 6 | 8 | Real pain (wrong numbers after a change); evidence is one data source (Fivetran dbt packages) |
| Accuracy (catch rate) | 5 | 7 | 22 of 63 real bug fixes confirmed (35%); 9 of 9 checked misses = missing rows in the sample (VERIFIED) |
| Precision (false alarms) | 4 | 8 | Study refactors: 2 flags, both real (good). Migration benchmark: 8 of 8 correct rewrites flagged (bad) (VERIFIED) |
| Usability | 6 | 8 | One command, skill, MCP, HTML report; but not on PyPI, noisy defaults, ~7.5 min on a real dbt package |
| Reliability | 7 | 8 | Two scale bugs found and fixed this week (memory, row budget); no real-world corpus in CI |
| Adoption | 2 | 5 | Zero outside users; version 0.6.0.dev0; not on PyPI |
| Verifiable outside evidence | 4 | 7 | Study data + method; no merged outside fix, no paper |
| EB-1A strength | 2-3 | 5 | No criterion met yet; a paper + public benchmark + merged fixes would change that |

## 3. Diagnosis: six root causes (each with evidence)

**P1. Identity: three products in one.** README leads with "evidence that an automated fix did what it claims"
(security + self-healing). Defaults reflect that: `attacks: bool = True` in `config.py`; 22 input categories
including `shell-metachar`, `attack`, `delimiter-mix`. All study evidence is about data changes. A buyer cannot
tell who it is for in 10 seconds. (VERIFIED in code/README.)

**P2. It cannot create the rows a bug needs.** Cases mutate the first 3 rows of the sample (`rows: int = 3`). In
9 of 9 hand-diagnosed misses, the bug needs a row combination absent from the sample (two accounts of a type, two
policies on one ticket, a non-null foreign key). No single-cell mutation can produce those. `exercise-check`
(merged) now *says* so; `exercise-synthesis` (unmerged) starts to *fix* it. This is the single biggest accuracy lever.

**P3. It cannot tell "malformed" from "different".** Migration benchmark (pandas -> Polars, 17 variants): every
correct migration FAILED, because inputs like `2_500`, `' 42 '` and `0.005` in an integer `id` crash a pinned Polars
schema while pandas accepts them. Those differences are real but irrelevant to most data teams, and they drown the
signal. Robustness findings and semantic findings share one verdict. (VERIFIED: run 1 results committed.)

**P4. The confidence score overstates certainty.** `score.py` uses the rule of three (95% bound ~ 3/n) as if the
~300 inputs were independent samples of real data. They are mutations of 3 rows. A typical PASS prints 99/100,
while the measured miss rate on real bug fixes is ~65%. A sceptical reviewer will see this as miscalibrated.

**P5. Adoption plumbing is missing.** Not on PyPI (install is a git URL, untested on a normal machine); README links
a GitHub Pages playground that only works once Pages is enabled (pending user step, not verifiable from the sandbox);
a real dbt package check takes ~7.5 min (jira: 455 s) — fine for CI, too slow for an agent loop or pre-commit.

**P6. Reliability is tested on toy inputs, not real ones.** Both bugs fixed this week (17 MB seed -> 5 GB memory;
rolling windows never exercised) surfaced only on real packages. There is no nightly real-world corpus in CI.

## 4. Strategy: one bold bet, two tracks

**Product bet: "the pull-request check that shows which numbers a dbt/SQL change moves — on edge cases your data
doesn't contain yet."** One audience (analytics engineers on dbt), one moment (the PR), one output (a comment).
Security attacks and self-healing stay as features, not the pitch.
Why it can win (INFERRED): dbt's own unit tests need hand-written expected rows; data-diff tools (Recce, Datafold)
compare against real data you already have and cannot invent the missing edge case. fixwitness needs neither.

**Evidence track (the EB-1A engine): turn the study into a public benchmark and a paper.** The 116-candidate
real-bug corpus from Fivetran's packages, the hand-read labels, and the finding that *test fixtures lack the
preconditions of most real bugs* are an original, reusable contribution. A citable dataset (DOI) plus a
peer-reviewed paper is evidence a stranger can verify; it does not depend on anyone merging a PR.

## 5. 90-day plan (engineering is mine; adoption steps are yours)

| # | Work | Done when (measured, not asserted) |
|---|---|---|
| E1 | **Data profile by default** for SQL/dbt/DataFrame: attacks off; semantic categories (null, empty, duplicate, duplicate-row, case, time-edge, flip, numeric pairs) decide the verdict; malformed-input findings go to a separate "robustness" section, not FAIL | Migration bench: correct rewrites PASS, wrong ones FAIL; study refactors: no new false alarms; study bug catches not lower |
| E2 | **Precondition synthesis from the SQL itself**: parse joins/filters (sqlglot) and add the rows they need (2 children per parent, ties on timestamps, a second row per key/type); merge `exercise-synthesis` after re-validation | Re-run the study: confirmed catches up from 22/63, false alarms on refactors still 0 new; every new catch hand-read |
| E3 | **Honest confidence**: replace rule-of-three with what was exercised (share of changed predicates/joins reached by an input) and the benchmark's measured miss rate | Report never shows 99/100 when the change's conditions were not exercised |
| E4 | **Speed**: compare only models downstream of the change, adaptive case budget, reuse the base build | Typical dbt PR < 2 min; jira package < 3 min |
| E5 | **Real-world corpus in CI**: nightly run on ~10 public dbt packages; crash/timeout/memory = failing build | Runs nightly; any regression opens an issue |
| E6 | **GitHub Action + PR comment** ("these 3 numbers changed, here is the smallest input") on the Marketplace | One-file install in a test repo, comment appears |
| A1 | YOU: PyPI v0.6.x release, GitHub Pages, Zendesk #284 PR | `pip install fixwitness` works on a clean laptop |
| A2 | YOU + me: 2-3 more upstream fixes (you supply open-issue links; I reproduce, fix, write proof) | Each PR approved by you before it is opened |
| R1 | Public benchmark release ("real dbt bug fixes + labels + harness") with a DOI | Others can run it with one command |
| R2 | Paper: empirical study + differential testing results + the fixture-gap finding; target a data-management or software-engineering venue (check deadlines; do not pay-to-publish) | Submitted; preprint public |
| A3 | Launch with one real story (benchmark + merged fixes + Action): dbt Slack, r/dataengineering, Show HN | Only after A1, E1, E6 |

Order: E1 -> E2 -> A1 -> E6 -> R1 -> R2, with E3-E5 alongside. E1 is first because nothing else matters while
correct changes FAIL.

## 6. Kill / pivot criteria (so we do not fool ourselves)
- After E1+E2: if confirmed catch rate on the study stays under ~45% **and** the migration bench still shows false
  alarms on correct rewrites, stop selling it as a product; publish it as a research artifact (R1, R2) and move on.
- If after launch (A3) no outside user files an issue or star growth is negligible within ~6 weeks, adoption is
  not the route; put the effort into the paper and upstream fixes.

## 7. What to stop
- Tuning the study numbers; reading famous, well-reviewed projects for bugs (OpenBB: nothing found).
- Adding new input formats or modes before E1-E3.
- Quoting the 99/100 confidence or any catch rate that is not hand-read.
