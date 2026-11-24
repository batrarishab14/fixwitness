## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `496a987a3767` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/ci/sample.profiles.yml` and 4 more. dbt project: changed `int_jira__field_history_scd`, `int_jira__issue_join`, `int_jira__pivot_daily_field_history`, `jira__daily_issue_field_history`, `jira__issue_enhanced`, `jira__timestamp_issue_field_history`; compared `jira__daily_issue_field_history`, `jira__daily_sprint_issue_history`, `jira__issue_enhanced`, `jira__issue_status_transitions`, `jira__project_enhanced`, `jira__sprint_enhanced`, `jira__timestamp_issue_field_history`, `jira__user_enhanced`; SQL on warehouse; tables `issue` (issue.csv), `priority` (priority.csv), `version` (version.csv), `resolution` (resolution.csv), `component` (component.csv), `issue_field_history` (issue_field_history.csv), `status` (status.csv), `team` (team.csv), `field` (field.csv), `issue_multiselect_history` (issue_multiselect_history.csv), `issue_type` (issue_type.csv), `user` (user.csv), `comment` (comment.csv), `sprint` (sprint.csv), `project` (project.csv), `status_category` (status_category.csv), `field_option` (field_option.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 296 comparable valid inputs give the same output |
| Not comparable | 4 valid inputs made the original fail too |

**Why:** the fix changes output on 296 valid inputs.

- Note: ignored column(s) jira__issue_status_transitions.transition_until, jira__timestamp_issue_field_history.valid_until: they change between two runs of the original on the same input
- Note: 4 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is sample as given, in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 000: `file-structure` input '<sample as given>' in `issue` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If the input has another column layout (<extra column at the end>), in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 001: `schema` input '<extra column at the end>' in `issue` (changed); input shrunk to the rows that show it
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `assignee` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 002: `delimiter-mix` input 'a; "b"' in `issue.assignee` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `creator` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 003: `delimiter-mix` input 'a; "b"' in `issue.creator` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `description` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 004: `delimiter-mix` input 'a; "b"' in `issue.description` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `key` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 005: `delimiter-mix` input 'a; "b"' in `issue.key` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `reporter` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 006: `delimiter-mix` input 'a; "b"' in `issue.reporter` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...
- **Values change.** If `summary` is 'a; "b"', in `jira__daily_issue_field_history`, columns `assignee`, `labels`, `collaborators`, `quarter` disappear and columns `summary`, `components` appear.
  - case 007: `delimiter-mix` input 'a; "b"' in `issue.summary` (changed)
  - jira__daily_issue_field_history: header: [['date_day', 'date_week', 'issue_id', 'source_relation', 'status', 'status_id', 'sprint', 'story_points', 'story_point_estimate', 'team', 'assignee', 'labe...
  - jira__issue_enhanced: header: [['issue_id', 'parent_issue_id', 'source_relation', 'original_estimate_seconds', 'remaining_estimate_seconds', 'time_spent_seconds', 'assignee_user_id', 'created_at', ...

Proof ID `0257dfbc9622e596` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/jira@v1.3.1/out/integration_tests_dbt_project/proof.json`
