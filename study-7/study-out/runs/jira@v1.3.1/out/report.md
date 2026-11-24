## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `assignee` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `496a987a3767` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/ci/sample.profiles.yml` and 4 more. dbt project: changed `int_jira__field_history_scd`, `int_jira__issue_join`, `int_jira__pivot_daily_field_history`, `jira__daily_issue_field_history`, `jira__issue_enhanced`, `jira__timestamp_issue_field_history`; compared `jira__daily_issue_field_history`, `jira__daily_sprint_issue_history`, `jira__issue_enhanced`, `jira__issue_status_transitions`, `jira__project_enhanced`, `jira__sprint_enhanced`, `jira__timestamp_issue_field_history`, `jira__user_enhanced`; SQL on warehouse; tables `issue` (issue.csv), `priority` (priority.csv), `version` (version.csv), `resolution` (resolution.csv), `component` (component.csv), `issue_field_history` (issue_field_history.csv), `status` (status.csv), `team` (team.csv), `field` (field.csv), `issue_multiselect_history` (issue_multiselect_history.csv), `issue_type` (issue_type.csv), `user` (user.csv), `comment` (comment.csv), `sprint` (sprint.csv), `project` (project.csv), `status_category` (status_category.csv), `field_option` (field_option.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 300 comparable valid inputs give the same output |

**Why:** the fix changes output on 300 valid inputs.

- Note: ignored column(s) jira__issue_status_transitions.transition_until, jira__timestamp_issue_field_history.valid_until: they change between two runs of the original on the same input

**What could go wrong:**

- **Values change.** If `assignee` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 000: `delimiter-mix` input 'a; "b"' in `issue.assignee` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `key` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 001: `delimiter-mix` input 'a; "b"' in `issue.key` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `reporter` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 002: `delimiter-mix` input 'a; "b"' in `issue.reporter` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `summary` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 003: `delimiter-mix` input 'a; "b"' in `issue.summary` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If an `issue` row has an empty `_fivetran_synced`, in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 004: `empty` input '' in `issue._fivetran_synced` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `_fivetran_synced` repeats the value of another row ('2020-11-06 22:23:38'), in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 005: `duplicate` input '2020-11-06 22:23:38' in `issue._fivetran_synced` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If two `issue` rows of the same group have `_fivetran_synced` = '2020-11-06 22:23:41' and '2020-11-06 22:23:41', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 006: `pairs` input '2020-11-06 22:23:41 | 2020-11-06 22:23:41' in `issue._fivetran_synced` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `assignee` has extra spaces ('  padded  '), in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 007: `whitespace` input '  padded  ' in `issue.assignee` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...

Proof ID `244955b06e15a442` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/jira@v1.3.1/out/integration_tests_dbt_project/proof.json`
