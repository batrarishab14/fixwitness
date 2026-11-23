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
