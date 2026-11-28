# fixwitness 0.6: development log (SQL queries and dbt models)

0.6 adds SQL and dbt support. The SQL benchmark in `benchmark/sql/` was written in the same session as the SQL input classes, and the classes were refined after seeing its results. **Every number here is a development result.** The held-out evaluation in `PROTOCOL_v0.6.md` measures how well 0.6 does on changes it has not seen.

The SQL benchmark has 6 queries and 17 changes: 6 correct and 11 wrong. Each wrong change models a well-known SQL pitfall:
- `COUNT(column)` instead of `COUNT(*)`;
- an inner join changed to a left join;
- a negated filter;
- a case-insensitive match;
- `NOT IN` with a NULL;
- a NULL treated as 0;
- `COUNT(*)` as an average's divisor;
- `UNION` instead of `UNION ALL`;
- join fan-out;
- de-duplicating the wrong table;
- a de-duplication that also changes the join type.

All runs below use SQLite. DuckDB runs in CI (`.github/workflows/sql.yml`).

| Run | Change made before the run | Wrong caught: fixwitness | Wrong caught: + expected | Correct rejected | What went wrong |
|---|---|---|---|---|---|
| 1 | First version: each table's cases from the 0.5 catalogue, a per-table cap, values a typed column can't hold skipped, all-NULL columns and repeated rows added | 9/11 | 10/11 | 1/6 | **Missed** `lower_status`: the "case" category's literal values (`UPPER`, `lower`) never matched `'paid'`, and the cap had dropped some cases. **False alarm** on Q04's reference: summing in another order changed the last float digit (`59.255` → `59.254999999999995`) |
| 2 | Cap keeps one case for every (column, category) pair before sampling; numbers compared with a relative tolerance of 1e-9 | 9/11 | 10/11 | 1/6 | **Still missed** `lower_status`. **False alarm** on Q06's reference: a numeric value (`10`) happened to equal another row's key, which made a duplicate key, the very category the case puts under review |
| 3 | A value that repeats another row's value counts as a duplicate key (follows the `duplicate` review setting); text columns also get their own value in other cases and with padding (`PAID`, `Paid`, ` paid`) | **10/11** | **11/11** | **0/6** | `distinct_orders` (de-duplicating the wrong table) is caught only with the expected result: on every non-incident input it behaves like the original, because duplicates are under review in that case |

Run 3 is the version described in the README. Each change is a general rule that applies to every table and column. None names a benchmark query or fix.

## Pipelines, warehouse dialects, DataFrames, JSON and Parquet

Added after the SQL runs above, in the same session, so that a change is checked wherever an agent makes it, not only in one dbt model. Like the rest of this log, everything here is development.

What was added:
- **A folder of models** (a dbt project): every model runs in dependency order, found from `ref()` and the tables after `FROM`/`JOIN`. The original's final models (no other model reads them) are compared, unless `sql_outputs` names others.
- **Warehouse dialects:** `dialect = "snowflake"` (or any sqlglot dialect) translates each query to the local engine. Names qualified with a database or schema are reduced to the loaded table.
- **DataFrame functions:** `function = "revenue"` calls the function with pandas, polars or PySpark DataFrames built from the tables, with the sample's column types. Each side uses the library it imports.
- **JSON and JSON Lines inputs:** cases change one value at a path. They add five JSON categories: `missing-key`, `null`, `json-type`, `json-escape`, `array`. Outputs that parse as JSON are compared by value.
- **Parquet inputs:** the typed-table cases, written back with the sample's schema. Parquet outputs are compared by value.

Changes made after seeing a result, each a general rule:

| Seen | Change |
|---|---|
| A pipeline test where the fix removed a model: the comparison reported a placeholder row instead of the missing model | A model one side does not have is left out of its output and reported as "only in the original's output" |
| An incident whose original runs but gives a wrong result (a SQL filter that misses `PAID`): the incident was reported as "not reproduced" although the expected result showed the original was wrong | When an expected output is given and the original's output differs from it, the original counts as failing on the incident |
| A JSON key that changes between runs (`run_at`) was ignored only when the output had several records: one JSON Lines record parses as an object, several as a list | Ignored keys match with or without array markers (`[].run_at` and `run_at` are the same key) |
| A pandas test capped at 80 cases missed `str.lower()`: the cap kept the catalogue value `UPPER` for the `case` category of `status`, not `PAID` | Under the cap, the one case kept for each (column, category) pair is the variant made from the sample's own value, when there is one |

The last change affects SQL mode too. It only changes which cases are kept when there are more than `max_cases`.

## Whole changes, dbt compiled by dbt, reproductions, faster DataFrame runs

- **`fixwitness check` with no file** checks every file the working tree changed: dbt projects, SQL files, changed DataFrame functions and scripts, each with the data files found by name. One verdict; files that are not code are listed with the reason. The same is the MCP tool `prove_change` and the GitHub Action with no `path` (which comments on the pull request).
- **dbt projects** are compiled by dbt itself (`dbt seed` + `dbt compile` with dbt-duckdb, for each version), or read from the manifests CI already has. Tested on dbt-labs' jaffle_shop in CI.
- **Every difference has a reproduction** under `repro/<case>/`: the input, both outputs, and the commands to re-run each side.
- **DataFrame runs** go through a server that imports pandas or polars once and forks a fresh process for each run (not for PySpark or `--no-network`). On the pandas test with 60 cases, the same 58 identical / 2 changed results in 5 s instead of about 30 s here; in CI, each pandas fix in `benchmark/complex/` took about 13 s instead of about 107 s, and each polars fix about 11 s instead of about 111 s, with the same verdicts.

Three CI failures on the first run with every library installed were in the tests, not in fixwitness. The polars and PySpark rewrites written as "correct" in two tests were not faithful to pandas: polars and Spark keep a group for a null key that pandas drops, Spark sums an all-NULL column to NULL where pandas gives 0, and neither matches null keys in a join. fixwitness reported the difference. The tests now use faithful rewrites, and one more test checks that the null-group rewrite fails. The third test expected a Parquet case that adds a column to keep the sample's exact schema.

## Findings people can act on, pairs of rows, and the columns a change touches

Added on 24 November 2026, still before the freeze:

- **Explanations and the smallest input.** Each difference is explained in a sentence with an impact label, and shrunk (delta debugging over rows) to the fewest rows that still show it. Neither changes a verdict.
- **Marking a difference as intended** (`[[accept]]` in `fixwitness.toml`): matching inputs become "review". This changes a verdict only when a user marks something; no benchmark uses it.
- **Pairs** (a new input category, valid by default): two rows of the same group, each with an unusual value. For numbers: 0.005 + 0.005, 2.675 + 1.005, 0.1 + 0.2, -0.5 + 0.5, and 9007199254740993 + 1 (beyond float precision). For text: the row's own value and its other-case or padded form. Made for a miss seen in development: `round_each` in `benchmark/complex/C05`, which rounds each amount before summing.
- **Diff-aware priority.** When there are more cases than `max_cases`, the cases of the columns named in the changed lines are kept before the seeded random sample. With fewer cases than the cap, nothing changes.

Benchmarks re-run after these changes (SQLite here):

| Benchmark | Fixes | Verdicts that changed |
|---|---|---|
| `benchmark/` (CSV scripts, including the 36 assistant fixes) | 92 | 0 |
| `benchmark/sql/` | 17 | 0 (after the fix below) |
| `benchmark/complex/` (pipeline, pandas, JSON Lines here) | 16 | 1: `round_each` is now caught (16 of 16 as labelled) |
| `benchmark/complex/` in CI (DuckDB, every library; commit a1da8fe) | 28 | 1: `round_each` is now caught (20 of 20 wrong caught, 0 of 8 correct rejected) |
| `benchmark/sql/` in CI (DuckDB; commit a1da8fe) | 17 | 0 (10 of 11, 11 of 11 with the expected result, 0 of 6) |

One false alarm appeared on the way and was fixed by a general rule. Q06's correct fix (one row per customer before the join) was rejected on pairs in `customers.name` and `customers.region`: the twin row repeats the customer's key, which is a duplicate key, and Q06 puts duplicates under review. Pairs now follow the `duplicate` review setting (and `duplicate-row` when the two values are equal), the way `delimiter-mix` follows the categories it combines. With that rule the SQL benchmark is back to 10/11, 11/11 with the expected result, and 0/6 correct fixes rejected. The CSV and complex results can't change under this rule: no CSV verdict depended on pairs, and the complex cases put nothing under review.

## Real dbt packages: what it took to run on them

Added on 24 November 2026, while preparing the real-repository study (`benchmark/realrepo/`), before
its counted run. Pilots on 8 of the frozen candidates and on two open bug reports were used only to
make fixwitness run on real packages; every change is general, and listed with the gap it closes:

| Gap seen on real packages | Change |
|---|---|
| Booleans and timestamps in seeds were loaded as text, so `not coalesce(_fivetran_deleted, false)` failed on every input | Seeds are loaded with the column types dbt gave them; two new kinds, boolean and timestamp, with their own cases (the other truth value; day, month and year boundaries, the epoch, clock changes) |
| Seed tables sampled one by one share no key values, so joins matched nothing | Keys are linked across tables when they don't join (the tables as given still run first) |
| A random private schema name compiled into `source_relation` looked like a difference | The name is normalized in compiled SQL |
| Old packages compile only on their supported warehouses | dbt compiles with the warehouse's own adapter (`--warehouse`), in a private schema dropped afterwards |
| Reserved words (`default`, `user`, `end`) as column and table names | Quoted; seed columns get the names the warehouse stored for dbt (a header written `"default"`) |
| Seed configs that test `target.name` | Targets are named after the adapter, as packages' own CI names them |
| Incremental models compiled as updates of themselves after the build | `dbt compile --full-refresh` |
| A mart read by another mart was never compared | Every published model downstream of a change is compared (not staging or intermediate) |
| dbt errors were reported as "`dbt seed` failed" with no reason | dbt's own explanation, and the full text in the summary |

Two changes reduce false alarms on real projects:

- **Your dbt tests are rules on the inputs.** `unique`, `not_null`, `accepted_values` and
  `unique_combination_of_columns` tests are traced back to the input column (through models that
  pass it through unchanged); inputs that break one are reviewed, not failed.
- **Every difference is checked twice.** The original is run again on the input; if its own output
  changes (ties in `row_number()`), the input is left out and reported.

And two make fixwitness more useful on bug fixes:

- **`--expect-change model.column`**: passes only when nothing else changes; the report shows what
  the fix changes, by example.
- **`fixwitness doctor`**: says what would be checked and the one command that fixes each gap.

Benchmarks are re-run in CI on the final commit; the numbers are in the README.

### Real-repository study: five runs (24 November 2026)

Candidates frozen before any run (`benchmark/realrepo/candidates.csv`); defaults only; every run reported as it came
out. Failing refactors and every flagged bug fix were read by hand (`runs/*/inspections.csv`, `bug_inspections.csv`).

| Run | Change before it | Bug fixes flagged / checked | Refactors flagged / checked |
|---|---|---|---|
| 1 | - | 22 / 48 | 4 / 22 (2 real, 2 false alarms) |
| 2 | false alarms fixed | 20 / 50 | 2 / 21 (real) |
| 3 | fair share of the case cap; ranked focus | 27 / 57 | 2 / 25 (real) |
| 4 | seed column order; edited models switched on | 31 / 63 | 2 / 25 (real) |
| 5 | switch-on limited to plain flags | 31 / 63 | 2 / 25 (real) |

What the runs showed (each verified by reproducing it):

- Run 2 lost two catches of run 1 (`stripe@v0.14.1`, `quickbooks@v1.2.1`). Cause: under the 300-case cap, cases were
  taken in table order, so a zero in `quantity` or a NULL `currency_id` never got a case. Fixed generally; both are
  caught again.
- Seeds whose header ends with a comma had every column shifted, because stored column names were sorted
  alphabetically. The original then failed on its own sample (`quickbooks@v0.19.0`, `workday@v0.1.1`).
- Models switched on by a variable that is off in the test project (`using_ticket_chat`) compiled to nothing, so the
  fix looked unchanged. The variables are now set for edited models; a first version set a list variable too and
  broke `mixpanel@v0.17.0`, caught by run 4.

Run 5, hand-read against the release notes: 22 of the 31 flagged bug fixes are the bug the note describes, 3 are in
the model the note names, 4 are unclear, 2 are not the bug. Confirmed 22 of 63 checked (35%), upper bound 49%.
The 32 misses were not yet analysed. Run 1's counted 22 were not read against the notes. "Flagged" means fixwitness
found a difference; a bug fix always changes behaviour, so a flag is not by itself proof it found the bug.

## 27 Nov: memory runaway on dbt_jira (study shard 5) fixed

Study shard 5 killed its runner on every run; jira@v1.10.3 alone reproduced it. Cause, found with
py-spy on a local reproduction (Postgres, same command as study.yml): every SQL case held its own
JSON bundle of *every* table, built before the 300-case cap. dbt_jira's `comment.csv` seed is 16.8 MB,
so each of thousands of candidate cases carried ~17 MB, and fixwitness passed 2.5 GB within 10 s of
starting case generation (5 GB cap reached in CI). Any user project with one large seed hits this.

Fix: a case's input may be a function that builds it when read (`cases._Content`); SQL cases share
one `tables` dict and keep only the small table they changed (`sql.lazy_bundle`). Verified locally:
jira@v1.10.3 now completes, peak fixwitness RSS ~783 MB (sampled every 5 s), PASS, 288 valid inputs,
0 changed (66 identical, 234 unstable: the original's own output varied between runs; not looked into).
Regression test `test_cases_do_not_each_hold_every_table`: old code 176 MB for 90 cases over a 2 MB
table (fails), new code under 40 MB (passes).

Guard: `run_study.py --memory-gb` (default 8) caps each candidate's address space, so a candidate that
runs out of memory is recorded "not checked: could not run: out of memory" instead of ending the shard.
Verified against the old code with `--memory-gb 3`: recorded in 13 s, shard continued.

## 27 Nov 2026: self-diagnosing check ("not exercisable with this data")
- New `src/fixwitness/exercise.py`; a PASS becomes INCONCLUSIVE when the change tests a value no input has, sits under
  an OR-free WHERE that keeps only such rows, or uses a column empty in every input (scoped to the tables the changed
  models read). `--no-exercise-check` / `exercise_check = false` turns it off. Proof field `exercise`; replayable.
- Local: 155 passed, 16 skipped (DuckDB not installed here). Existing tests exposed 3 false alarms (dbt config(), pandas
  kwarg, shell-to-Python rewrite); fixed, with regression tests.
- Real-data check (seeds only, raw model SQL, not the full generated cases) on dbt_quickbooks: v0.5.3 flagged for
  Accounts Payable/Receivable/UndepositedFunds (verified: no such seed rows); v0.9.1 flagged on `credit` (probably
  a seeds-only artifact); v0.12.2, v0.14.1, v1.6.2, v1.9.2 not flagged; refactor v1.8.1 not flagged. Other packages
  and the full-case run are NOT yet measured: CI `data` run and a study re-run are the next verification.
