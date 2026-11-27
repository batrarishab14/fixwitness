## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `id` is the number 0, in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 2 more cells). |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `bfea2ac56bd6` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 3 more. dbt project: changed `google_ads__keyword_report`; compared `google_ads__keyword_report`; SQL on warehouse; tables `account_history_data` (account_history_data.csv), `ad_group_criterion_history_data` (ad_group_criterion_history_data.csv), `keyword_stats_data` (keyword_stats_data.csv), `ad_group_history_data` (ad_group_history_data.csv), `campaign_history_data` (campaign_history_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 291 comparable valid inputs give the same output |
| Needs review | 9 of 9 inputs in review categories (inputs that break your dbt tests (stg_google_ads__keyword_stats: not_null(date_day); stg_google_ads__keyword_stats: unique_combination_of_columns(keyword_id, date_day))) differ |

**Why:** the fix changes output on 291 valid inputs.

**What could go wrong:**

- **Numbers change.** If `id` is the number 0, in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 2 more cells).
  - case 000: `numeric-format` input '0' in `account_history_data.id` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If `id` has extra spaces (' 42 '), in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 2 more cells).
  - case 001: `whitespace` input ' 42 ' in `account_history_data.id` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If an `account_history_data` row has an empty `id`, in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 2 more cells).
  - case 002: `empty` input '' in `account_history_data.id` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If two `account_history_data` rows of the same group have `id` = 9007199254740993 and 1, in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 5 more cells).
  - case 003: `pairs` input '9007199254740993 | 1' in `account_history_data.id` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If an `account_history_data` row has an empty `updated_at`, in `google_ads__keyword_report`, `account_id` for '2021-01-13' changes from 2121450128 to empty (and 2 more cells).
  - case 004: `empty` input '' in `account_history_data.updated_at` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If two `account_history_data` rows of the same group have `updated_at` = '2022-02-01 2:20:51' and '2022-02-01 2:20:51', in `google_ads__keyword_report`, `account_id` for '2021-01-12' changes from 2121450128 to empty (and 59 more cells).
  - case 005: `pairs` input '2022-02-01 2:20:51 | 2022-02-01 2:20:51' in `account_history_data.updated_at` (changed); input shrunk to the rows that show it
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If an `account_history_data` row has an empty `_fivetran_synced`, in `google_ads__keyword_report`, `account_id` for '2021-01-12' changes from 2121450128 to empty (and 29 more cells).
  - case 006: `empty` input '' in `account_history_data._fivetran_synced` (changed)
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''
- **Numbers change.** If two `account_history_data` rows of the same group have `_fivetran_synced` = '2022-02-01 2:20:52' and '2022-02-01 2:20:52', in `google_ads__keyword_report`, `account_id` for '2021-01-12' changes from 2121450128 to empty (and 29 more cells).
  - case 007: `pairs` input '2022-02-01 2:20:52 | 2022-02-01 2:20:52' in `account_history_data._fivetran_synced` (changed)
  - google_ads__keyword_report: row 1, account_id: '2121450128' -> ''
  - google_ads__keyword_report: row 1, campaign_id: '344106493' -> ''

Proof ID `62494c9c35e01884` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/google_ads@v0.9.1/out/integration_tests_dbt_project/proof.json`
