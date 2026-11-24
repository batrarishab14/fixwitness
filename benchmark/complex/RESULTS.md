# fixwitness benchmark: pipelines, dialects, DataFrames, JSON and Parquet

fixwitness 0.6.0.dev0 · SQL engine sqlite · 16 fixes across 3 cases (5 correct, 11 wrong) · run time 218s

Development results: the cases were written in the same session as the 0.6 features. The wrong fixes are **synthetic**: each models a well-known pitfall, named per fix below. None was produced by an AI assistant.

Skipped (libraries not installed here): C02-snowflake-dialect (needs sqlglot); C04-pandas-to-polars (needs polars); C06-parquet-orders (needs pyarrow).

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| job runs | 0/11 (0%) | 0/5 (0%) |
| sample test | 0/11 (0%) | 0/5 (0%) |
| fixwitness | 11/11 (100%) | 0/5 (0%) |

## Every fix

| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | Caught by |
|---|---|---|---|---|---|---|---|
| C01-dbt-pipeline | cte_mart | correct | the mart rewritten with CTEs | accept | accept | accept | - |
| C01-dbt-pipeline | distinct_staging | wrong | DISTINCT added to a staging model (repeated rows collapse) | accept | accept | **reject** | duplicate-row, pairs |
| C01-dbt-pipeline | left_join_mart | wrong | an inner join changed to a left join in the mart | accept | accept | **reject** | empty, file-structure, null-column, numeric-format, pairs, whitespace |
| C01-dbt-pipeline | not_refunded | wrong | a filter rewritten as its negation (other statuses now pass) | accept | accept | **reject** | case, csv-structure, delimiter-mix, long, pairs, punctuation, quotes, shell-metachar, unicode, whitespace |
| C01-dbt-pipeline | split_model | correct | a staging model split in two | accept | accept | accept | - |
| C03-pandas-revenue | count_amount.py | wrong | size() replaced by count() of a column with missing values | accept | accept | **reject** | empty, null-column |
| C03-pandas-revenue | drop_duplicates.py | wrong | drop_duplicates() added (repeated rows collapse) | accept | accept | **reject** | duplicate-row, pairs |
| C03-pandas-revenue | dropna.py | wrong | dropna() on the whole frame (rows with any missing value are lost) | accept | accept | **reject** | empty, null-column |
| C03-pandas-revenue | left_merge.py | correct | a left merge: orders without a customer get no region, and groupby drops missing keys | accept | accept | accept | - |
| C03-pandas-revenue | query_merge.py | correct | filter with query(), merge the other way round, aggregate in two steps | accept | accept | accept | - |
| C03-pandas-revenue | str_lower.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C05-jsonl-events | float_amount.py | wrong | float() around each amount (large integers lose precision) | accept | accept | **reject** | numeric-format, pairs |
| C05-jsonl-events | generator.py | correct | a defaultdict and a generator | accept | accept | accept | - |
| C05-jsonl-events | lower_status.py | wrong | a case-insensitive status match | accept | accept | **reject** | case, pairs |
| C05-jsonl-events | round_each.py | wrong | each amount rounded before summing instead of the total | accept | accept | **reject** | pairs |
| C05-jsonl-events | strict_key.py | wrong | e.get('status') replaced by e['status'] (a record without the key now fails) | accept | accept | **reject** | missing-key |
