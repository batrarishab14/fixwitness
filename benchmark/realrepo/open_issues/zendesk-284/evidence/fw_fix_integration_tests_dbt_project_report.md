## fixwitness: PASS, confidence 99/100 (HIGH)

`integration_tests`: commit `c5f2cfa03a16` (original) vs working tree (fix); changed: `integration_tests/tests/integrity/ticket_summary_unreplied_count_match.sql`, `models/zendesk__ticket_summary.sql`. dbt project: changed `zendesk__ticket_summary`; compared `zendesk__ticket_summary`; SQL on duckdb; tables `time_zone_data` (time_zone_data.csv), `ticket_schedule_data` (ticket_schedule_data.csv), `organization_tag_data` (organization_tag_data.csv), `domain_name_data` (domain_name_data.csv), `ticket_comment_data` (ticket_comment_data.csv), `organization_data` (organization_data.csv), `user_tag_data` (user_tag_data.csv), `schedule_data` (schedule_data.csv), `daylight_time_data` (daylight_time_data.csv), `ticket_data` (ticket_data.csv), `ticket_field_history_data` (ticket_field_history_data.csv), `ticket_tag_data` (ticket_tag_data.csv), `brand_data_postgres` (brand_data_postgres.csv), `group_data` (group_data.csv), `ticket_form_history_data` (ticket_form_history_data.csv), `schedule_holiday_data` (schedule_holiday_data.csv), `user_data` (user_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | PASS: 283 of 283 comparable valid inputs give the same output apart from the expected change |
| Expected change | 272 inputs changed only `zendesk__ticket_summary.unreplied_ticket_count`, `zendesk__ticket_summary.unreplied_unsolved_ticket_count` |
| Not comparable | 10 valid inputs made the original fail too |
| Needs review | 0 of 7 inputs in review categories (inputs that break your dbt tests (stg_zendesk__domain_name: not_null(organization_id); stg_zendesk__organization: not_null(organization_id); stg_zendesk__ticket_comment: not_null(ticket_comment_id); stg_zendesk__time_zone: not_null(time_zone))) differ |

- Note: 10 valid inputs could not be compared because the original failed on them

**What the fix changes (as expected):**

- case 000: `file-structure` input '<tables as given>' in `None`
  - zendesk__ticket_summary: row 1, unreplied_ticket_count: '0' -> '3'
- case 001: `file-structure` input '<sample as given>' in `time_zone_data`
  - zendesk__ticket_summary: row 1, unreplied_ticket_count: '0' -> '3'
- case 002: `schema` input '<extra column at the end>' in `time_zone_data`
  - zendesk__ticket_summary: row 1, unreplied_ticket_count: '0' -> '3'

Confidence: 283 valid inputs gave the same output, evidence strength 0.989 (rule of three), reproduction factor 1.0.

Proof ID `611f2390494e94af` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/issues/zendesk-284/fw_fix/integration_tests_dbt_project/proof.json`
