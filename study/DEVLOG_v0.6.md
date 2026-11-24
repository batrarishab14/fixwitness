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
