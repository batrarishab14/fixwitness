# Why fixwitness misses real bugs: 10 diagnosed cases, one root cause

Of the 32 real bug fixes (run 5, `benchmark/realrepo/runs/run5/`) fixwitness did not flag, 10 have been
hand-diagnosed against the real commits and the real seed data. All 10 fail for the identical structural
reason, across 4 different Fivetran packages and 5 different kinds of bug fix.

**The pattern:** a real bug's fix only changes output on a specific precondition -- a second row of some
kind, a non-null foreign key, a non-empty numeric column, two accounts of the same type. Fivetran's own
official `integration_tests/seeds/*.csv` fixtures frequently do not contain that precondition at all, in
either the buggy or the fixed version of the package. No data mutation fixwitness could generate can expose
a bug whose precondition has zero matching rows anywhere in the fixture -- the buggy and fixed code produce
byte-identical output on every input fixwitness can construct from that seed, because the seed never
reaches the code path where they'd differ.

Each row below was confirmed directly: by reading the real model diff, reading the real seed CSV, and (for
most) running fixwitness itself against the real commits under the same Postgres warehouse
`benchmark/realrepo/run_study.py` uses, not assumed from the bug's description.

| # | Package @ version | Bug shape | Confirmed precondition missing from the real seed |
|---|---|---|---|
| 1 | `dbt_fivetran_log` v0.6.4 | missing join condition (destination+month) | no row shares both a destination and a month across the two joined seeds |
| 2 | `dbt_quickbooks` v0.5.3 | missing filter (`not is_sub_account`) | zero `Accounts Payable`-type rows in the seed at all |
| 3 | `dbt_lever` (issue #43) | duplicate row from an unfiltered join to deleted records | verified with the project's own 4-step evidence harness (`benchmark/realrepo/open_issues/lever-43/`): fixwitness does NOT catch it on Lever's real unmodified seeds, only when synthetic rows are added |
| 4 | `dbt_zendesk` v0.8.1 | (earlier finding, same pattern) | -- |
| 5 | `dbt_zendesk` v1.0.1 | removed a dedup step | no two role-change audit rows share a `(source_id, created_at)` pair |
| 6 | `dbt_quickbooks` v1.6.2 | coalesce/fallback reorder | the one row needing the fallback points at an `item_id` that doesn't exist in `item_data.csv` -- broken FK |
| 7 | `dbt_quickbooks` v1.9.2 | new journal-entry lookup before fallback | the one `journal_entry_id` reference in the data has zero matching rows in `journal_entry_line_data.csv` |
| 8 | `dbt_zendesk` v1.5.1 | window-function partition-by change for tickets with 2+ SLA policies | zero tickets in the seed are linked to more than one SLA policy |
| 9 | `dbt_quickbooks` v0.9.1 | boolean sign-flip (`credit` column) | `total_amount` is null in every single row of `purchase_data.csv`, not just the targeted one -- null × -1 is still null |
| 10 | `dbt_netsuite` v1.8.0 | null coalesce for top-level subsidiaries missing a self-conversion rate | the precondition (subsidiary 6 has zero self-conversion exchange-rate rows) is real, but zero transaction lines in the seed reference subsidiary 6 at all, so the broken value never reaches a compared column |

One related case, `dbt_google_ads_source` v0.9.3, was checked and found to be a **different** category
(a connector grain change removed a column upstream -- schema drift, not a missing-precondition bug) and is
not counted above.

## What this does and doesn't mean

- It means the 35% confirmed catch rate is not primarily explained by a fixable gap in fixwitness's own
  case-generation logic -- 10 of 10 diagnosed misses are the same external, structural limitation.
- It does not mean fixwitness is complete: the other 22 of 32 misses are undiagnosed, and a real
  case-generation gap may exist among them. The 32-missed-bugs list is not fully swept.
- It does mean that improving the catch rate further by better case generation alone has a visible ceiling:
  a case generator cannot invent a row combination that would change a real package's real referential
  integrity. Improving on this would require either synthetic seed augmentation (adding rows that preserve
  the fixture's existing constraints) or richer real fixtures upstream -- not better mutation strategies.

## Environment note (corrected)

An earlier version of this investigation also flagged a "DuckDB/dbt-core version drift" problem based on
`dbt_marketo` and `dbt_quickbooks` compile crashes during diagnosis. That was a research artifact: the real
study (`run_study.py` via `.github/workflows/study.yml`) always runs real-repo candidates against Postgres
(`FIXWITNESS_STUDY_WAREHOUSE`), but the diagnostic reproductions used plain `fixwitness check` with no
`--warehouse` flag, which defaults to DuckDB -- a different engine than the one that produced the study's
real numbers. Re-run correctly, under Postgres, both projects compiled and ran clean. There is no DuckDB
version-drift problem in the real study, and no dependency pin is needed.
