# fixwitness SQL benchmark results

fixwitness 0.5.0 · engine sqlite · 17 fixes across 6 cases (6 correct, 11 wrong) · run time 151s

The wrong fixes are **synthetic**: each models a well-known SQL pitfall, named per fix below. None was produced by an AI agent.

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| job runs | 0/11 (0%) | 0/6 (0%) |
| sample test | 0/11 (0%) | 0/6 (0%) |
| fixwitness | 10/11 (91%) | 0/6 (0%) |
| fixwitness+exp | 11/11 (100%) | 0/6 (0%) |

## Every fix

| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | +exp | Caught by |
|---|---|---|---|---|---|---|---|---|
| Q01-revenue-refactor | count_column.sql | wrong | COUNT(column) instead of COUNT(*): rows with a NULL amount stop being counted | accept | accept | **reject** | **reject** | empty, null-column |
| Q01-revenue-refactor | left_join.sql | wrong | join type changed: a LEFT JOIN keeps orders whose customer is missing | accept | accept | **reject** | **reject** | duplicate, empty, file-structure, null-column, numeric-format, whitespace |
| Q01-revenue-refactor | lower_status.sql | wrong | case-insensitive match added: 'PAID' and 'Paid' now count as paid | accept | accept | **reject** | **reject** | case |
| Q01-revenue-refactor | negated_filter.sql | wrong | filter rewritten as a negation: status <> 'refunded' admits every other status | accept | accept | **reject** | **reject** | case, csv-structure, delimiter-mix, long, punctuation, quotes, shell-metachar, unicode, whitespace |
| Q01-revenue-refactor | reference.sql | correct | the filter moved into a CTE; same joins and aggregates | accept | accept | accept | accept | - |
| Q02-not-exists-rewrite | not_in.sql | wrong | NOT IN with a subquery: one NULL in blocked.customer_id makes it return no rows | accept | accept | **reject** | **reject** | empty, null-column |
| Q02-not-exists-rewrite | reference.sql | correct | anti-join with LEFT JOIN ... IS NULL | accept | accept | accept | accept | - |
| Q03-average-rewrite | coalesce_zero.sql | wrong | NULL treated as 0: missing ratings become 0 stars | accept | accept | **reject** | **reject** | empty, null-column |
| Q03-average-rewrite | count_star.sql | wrong | COUNT(*) as the divisor: NULL ratings now pull the average down | accept | accept | **reject** | **reject** | empty |
| Q03-average-rewrite | reference.sql | correct | SUM over COUNT of the same column (both skip NULLs) | accept | accept | accept | accept | - |
| Q04-union-total | reference.sql | correct | sum of per-channel sums (NULL when both are empty, like the original) | accept | accept | accept | accept | - |
| Q04-union-total | union_distinct.sql | wrong | UNION instead of UNION ALL: equal amounts are counted once | accept | accept | **reject** | **reject** | duplicate, duplicate-row, numeric-format |
| Q05-exists-to-join | inner_join.sql | wrong | join fan-out: a customer with two addresses doubles their orders | accept | accept | **reject** | **reject** | duplicate, duplicate-row, numeric-format |
| Q05-exists-to-join | reference.sql | correct | semi-join written as IN (no fan-out) | accept | accept | accept | accept | - |
| Q06-incident-duplicate-customers | dedupe_left_join.sql | wrong | de-duplicates customers but also switches to a LEFT JOIN | accept | accept | **reject** | **reject** | empty, file-structure, null-column, numeric-format, whitespace |
| Q06-incident-duplicate-customers | distinct_orders.sql | wrong | de-duplicates the wrong table: orders instead of customers | accept | accept | accept | **reject** | - |
| Q06-incident-duplicate-customers | reference.sql | correct | one row per customer before the join | accept | accept | accept | accept | - |
