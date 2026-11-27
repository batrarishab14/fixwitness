## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `github__daily_metrics`, `sum_days_issue_open` for '2018-11-24T00:00:00' changes from 2925.08712962963 to 2925.0871412037036 (and 41 more cells). |

Not checked: `CHANGELOG.md` (documentation)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `073c44e7b5bb` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `integration_tests/dbt_project.yml`, `models/intermediate/int_github__issue_joined.sql`. dbt project: changed `github__issues`, `github__pull_requests`; compared `github__daily_metrics`, `github__issues`, `github__monthly_metrics`, `github__pull_requests`, `github__quarterly_metrics`, `github__weekly_metrics`; SQL on warehouse; tables `github_requested_reviewer_history_data` (github_requested_reviewer_history_data.csv), `github_issue_comment_data` (github_issue_comment_data.csv), `github_label_data` (github_label_data.csv), `github_issue_assignee_data` (github_issue_assignee_data.csv), `github_pull_request_data` (github_pull_request_data.csv), `github_team_data` (github_team_data.csv), `github_issue_label_data` (github_issue_label_data.csv), `github_issue_closed_history_data` (github_issue_closed_history_data.csv), `github_issue_merged_data` (github_issue_merged_data.csv), `github_repository_data` (github_repository_data.csv), `github_repo_team_data` (github_repo_team_data.csv), `github_user_data` (github_user_data.csv), `github_issue_data` (github_issue_data.csv), `github_pull_request_review_data` (github_pull_request_review_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 31 of 229 comparable valid inputs give the same output |
| Needs review | 40 of 54 inputs in review categories (inputs that break your dbt tests (stg_github__issue: not_null(issue_id); stg_github__issue: unique(issue_id); stg_github__issue_closed_history: unique_combination_of_columns(issue_id, updated_at); stg_github__issue_comment: not_null(issue_comment_id))) differ |

**Why:** the fix changes output on 198 valid inputs.

- Note: 19 inputs were left out: on them the original's own output changes from run to run (for example ties in ORDER BY or row_number()), so a difference there is not the change's (cases 148, 168, 221, 222, 224, 228, 233, 234)

**What could go wrong:**

- **Numbers change.** If the file is tables as given, in `github__daily_metrics`, `sum_days_issue_open` for '2018-11-24T00:00:00' changes from 2925.08712962963 to 2925.0871412037036 (and 41 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Numbers change.** If a `github_requested_reviewer_history_data` row has an empty `created_at`, in `github__daily_metrics`, `sum_days_pr_open` for '2019-12-09T00:00:00' changes from 2544.6682523148147 to 2544.6682638888888 (and 9 more cells).
  - case 001: `empty` input '' in `github_requested_reviewer_history_data.created_at` (changed); input shrunk to the rows that show it
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If `created_at` repeats the value of another row ('2019-12-14 02:07:16'), in `github__issues`, `url_link` for 713211321 changes from 'https://github.com/2463fd7267062bf80a12…' to 'https://github.com/2463fd7267062bf80a12…'.
  - case 002: `duplicate` input '2019-12-14 02:07:16' in `github_requested_reviewer_history_data.created_at` (changed); input shrunk to the rows that show it
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If two `github_requested_reviewer_history_data` rows of the same group have `created_at` = '2019-03-03 12:58:01' and '2019-03-03 12:58:01', in `github__issues`, `url_link` for 592969404 changes from 'https://github.com/6e5ef3e6ef42a78ea2e2…' to 'https://github.com/6e5ef3e6ef42a78ea2e2…' (and 29 more cells).
  - case 003: `pairs` input '2019-03-03 12:58:01 | 2019-03-03 12:58:01' in `github_requested_reviewer_history_data.created_at` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If `pull_request_id` is the number 0, in `github__issues`, `url_link` for 592969404 changes from 'https://github.com/6e5ef3e6ef42a78ea2e2…' to 'https://github.com/6e5ef3e6ef42a78ea2e2…' (and 29 more cells).
  - case 004: `numeric-format` input '0' in `github_requested_reviewer_history_data.pull_request_id` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If `pull_request_id` has extra spaces (' 42 '), in `github__issues`, `url_link` for 592969404 changes from 'https://github.com/6e5ef3e6ef42a78ea2e2…' to 'https://github.com/6e5ef3e6ef42a78ea2e2…' (and 29 more cells).
  - case 005: `whitespace` input ' 42 ' in `github_requested_reviewer_history_data.pull_request_id` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If a `github_requested_reviewer_history_data` row has an empty `pull_request_id`, in `github__issues`, `url_link` for 592969404 changes from 'https://github.com/6e5ef3e6ef42a78ea2e2…' to 'https://github.com/6e5ef3e6ef42a78ea2e2…' (and 29 more cells).
  - case 006: `empty` input '' in `github_requested_reviewer_history_data.pull_request_id` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
- **Values change.** If `pull_request_id` repeats the value of another row (398307573), in `github__issues`, `url_link` for 592969404 changes from 'https://github.com/6e5ef3e6ef42a78ea2e2…' to 'https://github.com/6e5ef3e6ef42a78ea2e2…' (and 29 more cells).
  - case 007: `duplicate` input '398307573' in `github_requested_reviewer_history_data.pull_request_id` (changed)
  - github__issues: row 1, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...
  - github__issues: row 2, url_link: 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...' -> 'https://github.com/6e5ef3e6ef42a78ea2e20ed87de04a989e4712e28889db0f0b754341fe...

Proof ID `e3c7ad435b8b9e01` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/github@v0.5.1/out/integration_tests_dbt_project/proof.json`
