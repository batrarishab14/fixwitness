## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears. |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `a9628976d152` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html` and 5 more. dbt project: changed `int_jira__agg_multiselect_history`, `int_jira__issue_join`, `jira__daily_issue_field_history`, `jira__issue_enhanced`; compared `jira__daily_issue_field_history`, `jira__issue_enhanced`, `jira__project_enhanced`, `jira__user_enhanced`; SQL on warehouse; tables `issue` (issue.csv), `priority` (priority.csv), `version` (version.csv), `resolution` (resolution.csv), `component` (component.csv), `issue_field_history` (issue_field_history.csv), `status` (status.csv), `field` (field.csv), `issue_multiselect_history` (issue_multiselect_history.csv), `issue_type` (issue_type.csv), `user` (user.csv), `comment` (comment.csv), `sprint` (sprint.csv), `project` (project.csv), `status_category` (status_category.csv), `field_option` (field_option.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 291 comparable valid inputs give the same output |
| Not comparable | 2 valid inputs made the original fail too |
| Needs review | 7 of 7 inputs in review categories (inputs that break your dbt tests (stg_jira__comment: unique(comment_id); stg_jira__issue_field_history: unique_combination_of_columns(field_id, issue_id, updated_at); stg_jira__issue_multiselect_history: unique_combination_of_columns(_fivetran_id, updated_at))) differ |

**Why:** the fix changes output on 291 valid inputs.

- Note: 2 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is tables as given, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If the file is sample as given, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 001: `file-structure` input '<sample as given>' in `issue` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If the input has another column layout (<extra column at the end>), in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 002: `schema` input '<extra column at the end>' in `issue` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `assignee` is 'a; "b"', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 003: `delimiter-mix` input 'a; "b"' in `issue.assignee` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `creator` is 'a; "b"', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 004: `delimiter-mix` input 'a; "b"' in `issue.creator` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `description` is 'a; "b"', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 005: `delimiter-mix` input 'a; "b"' in `issue.description` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `key` is 'a; "b"', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 006: `delimiter-mix` input 'a; "b"' in `issue.key` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `reporter` is 'a; "b"', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 007: `delimiter-mix` input 'a; "b"' in `issue.reporter` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...

Proof ID `1d1224c74e3f681b` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/jira@v0.12.2/out/integration_tests_dbt_project/proof.json`
