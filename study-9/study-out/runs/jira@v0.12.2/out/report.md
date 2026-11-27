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
| Data unchanged | FAIL: 0 of 219 comparable valid inputs give the same output |
| Needs review | 81 of 81 inputs in review categories (inputs that break your dbt tests (stg_jira__comment: not_null(comment_id); stg_jira__comment: unique(comment_id); stg_jira__component: not_null(component_id); stg_jira__component: unique(component_id))) differ |

**Why:** the fix changes output on 219 valid inputs.

**What could go wrong:**

- **Values change.** If the file is tables as given, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `id` is the number 0, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 001: `numeric-format` input '0' in `issue.id` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If an `issue` row has an empty `id`, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 002: `empty` input '' in `issue.id` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `id` repeats the value of another row (10011), in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 003: `duplicate` input '10011' in `issue.id` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If two `issue` rows of the same group have `id` = 9007199254740993 and 1, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 004: `pairs` input '9007199254740993 | 1' in `issue.id` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If an `issue` row has an empty `_fivetran_synced`, in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 005: `empty` input '' in `issue._fivetran_synced` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If `_fivetran_synced` repeats the value of another row ('2020-11-06 22:23:38'), in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 006: `duplicate` input '2020-11-06 22:23:38' in `issue._fivetran_synced` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...
- **Values change.** If two `issue` rows of the same group have `_fivetran_synced` = '2020-11-06 22:23:41' and '2020-11-06 22:23:41', in `jira__daily_issue_field_history`, column `components` disappears and column `component` appears.
  - case 007: `pairs` input '2020-11-06 22:23:41 | 2020-11-06 22:23:41' in `issue._fivetran_synced` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'issue_id', 'status', 'sprint', 'summary', 'components', 'story_points', 'issue_day_id']] -> [['date_day', 'issue_id', 'status', 'component', ...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', 'resolved_at', 'cre...

Proof ID `28914f83242edfbe` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/jira@v0.12.2/out/integration_tests_dbt_project/proof.json`
