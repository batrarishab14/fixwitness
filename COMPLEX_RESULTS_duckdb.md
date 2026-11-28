# fixwitness benchmark: pipelines, dialects, DataFrames, JSON and Parquet

fixwitness 0.6.0.dev0 · SQL engine duckdb · 28 fixes across 6 cases (8 correct, 20 wrong) · run time 865s

Development results: the cases were written in the same session as the 0.6 features. The wrong fixes are **synthetic**: each models a well-known pitfall, named per fix below. None was produced by an AI assistant.

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| job runs | 0/20 (0%) | 0/8 (0%) |
| sample test | 1/20 (5%) | 0/8 (0%) |
| fixwitness | 20/20 (100%) | 0/8 (0%) |

## Every fix

| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | Caught by |
|---|---|---|---|---|---|---|---|
| C01-dbt-pipeline | cte_mart | correct | the mart rewritten with CTEs | accept | accept | accept | - |
| C01-dbt-pipeline | distinct_staging | wrong | DISTINCT added to a staging model (repeated rows collapse) | accept | accept | **reject** | duplicate-row, pairs |
| C01-dbt-pipeline | left_join_mart | wrong | an inner join changed to a left join in the mart | accept | accept | **reject** | empty, file-structure, null-column, numeric-format, pairs, whitespace |
| C01-dbt-pipeline | not_refunded | wrong | a filter rewritten as its negation (other statuses now pass) | accept | accept | **reject** | case, csv-structure, delimiter-mix, long, pairs, punctuation, quotes, shell-metachar, unicode, whitespace |
| C01-dbt-pipeline | split_model | correct | a staging model split in two | accept | accept | accept | - |
| C02-snowflake-dialect | case_when.sql | correct | IFF and COUNT_IF written as CASE expressions | accept | accept | accept | - |
| C02-snowflake-dialect | count_star.sql | wrong | COUNT_IF replaced by COUNT(*) over a filtered join (unpaid-only regions disappear) | accept | **reject** | **reject** | delimiter-mix, duplicate, empty, file-structure, numeric-format, pairs, schema, whitespace |
| C02-snowflake-dialect | ilike.sql | wrong | = changed to ILIKE (case-insensitive match) | accept | accept | **reject** | case, pairs |
| C02-snowflake-dialect | zero_null_amount.sql | wrong | a NULL amount treated as 0 (an all-NULL sum becomes 0) | accept | accept | **reject** | null-column |
| C03-pandas-revenue | count_amount.py | wrong | size() replaced by count() of a column with missing values | accept | accept | **reject** | empty, null-column |
| C03-pandas-revenue | drop_duplicates.py | wrong | drop_duplicates() added (repeated rows collapse) | accept | accept | **reject** | duplicate-row, pairs |
| C03-pandas-revenue | dropna.py | wrong | dropna() on the whole frame (rows with any missing value are lost) | accept | accept | **reject** | empty, null-column |
| C03-pandas-revenue | left_merge.py | correct | a left merge: orders without a customer get no region, and groupby drops missing keys | accept | accept | accept | - |
| C03-pandas-revenue | query_merge.py | correct | filter with query(), merge the other way round, aggregate in two steps | accept | accept | accept | - |
| C03-pandas-revenue | str_lower.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C04-pandas-to-polars | polars_count.py | wrong | pl.col(...).count() counts non-null values, not rows | accept | accept | **reject** | empty, null-column |
| C04-pandas-to-polars | polars_len.py | correct | filter, join (null keys match, as in pandas) and group_by with pl.len() | accept | accept | accept | - |
| C04-pandas-to-polars | polars_lower.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C04-pandas-to-polars | polars_null_group.py | wrong | polars keeps the null group that pandas groupby drops | accept | accept | **reject** | null-column |
| C05-jsonl-events | float_amount.py | wrong | float() around each amount (large integers lose precision) | accept | accept | **reject** | numeric-format, pairs |
| C05-jsonl-events | generator.py | correct | a defaultdict and a generator | accept | accept | accept | - |
| C05-jsonl-events | lower_status.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C05-jsonl-events | round_each.py | wrong | each amount rounded before summing instead of the total | accept | accept | **reject** | pairs |
| C05-jsonl-events | strict_key.py | wrong | e.get('status') replaced by e['status'] (a record without the key now fails) | accept | accept | **reject** | missing-key |
| C06-parquet-orders | fill_null.py | wrong | missing amounts written as 0 | accept | accept | **reject** | empty, null-column, schema |
| C06-parquet-orders | int32_ids.py | wrong | order_id narrowed to int32 (large ids overflow) | accept | accept | **reject** | schema |
| C06-parquet-orders | lower.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C06-parquet-orders | pylist.py | correct | rows filtered in Python and written with the same schema | accept | accept | accept | - |
