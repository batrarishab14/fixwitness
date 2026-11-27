## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | not exercisable with this data: no input reaches what the change touched ('next_reply_time', 'not set'), so identical output proves nothing about it; add rows that have it |

Not checked: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `.gitignore` (not code); `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `1a57d7f4533c` (original) vs working tree (fix); changed: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md`, `.github/workflows/auto-release.yml`, `.github/workflows/generate-docs.yml`, `.gitignore`, `CHANGELOG.md` and 14 more. dbt project: changed `int_zendesk__agent_work_time_business_hours`, `int_zendesk__reply_time_business_hours`, `int_zendesk__requester_wait_time_business_hours`, `zendesk__sla_policies`, `zendesk__ticket_metrics`; compared `zendesk__sla_policies`, `zendesk__ticket_metrics`, `zendesk__ticket_summary`; SQL on warehouse; tables `time_zone_data` (time_zone_data.csv), `ticket_schedule_data` (ticket_schedule_data.csv), `organization_tag_data` (organization_tag_data.csv), `domain_name_data` (domain_name_data.csv), `ticket_comment_data` (ticket_comment_data.csv), `organization_data` (organization_data.csv), `user_tag_data` (user_tag_data.csv), `schedule_data` (schedule_data.csv), `daylight_time_data` (daylight_time_data.csv), `ticket_data` (ticket_data.csv), `ticket_field_history_data` (ticket_field_history_data.csv), `ticket_tag_data` (ticket_tag_data.csv), `brand_data_postgres` (brand_data_postgres.csv), `group_data` (group_data.csv), `ticket_form_history_data` (ticket_form_history_data.csv), `schedule_holiday_data` (schedule_holiday_data.csv), `user_data` (user_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | PASS: 302 of 302 comparable valid inputs give the same output |
| Not comparable | 2 valid inputs made the original fail too |
| Needs review | 0 of 8 inputs in review categories () differ |

**Why:** not exercisable with this data: no input reaches what the change touched ('next_reply_time', 'not set'), so identical output proves nothing about it; add rows that have it.

- Note: ignored column(s) zendesk__ticket_metrics.assignee_last_login_age_minutes, zendesk__ticket_metrics.requester_last_login_age_minutes: they change between two runs of the original on the same input
- Note: 2 valid inputs could not be compared because the original failed on them

Proof ID `327d20a3fdd22105` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/zendesk@v0.25.0-a1/out/integration_tests_dbt_project/proof.json`
