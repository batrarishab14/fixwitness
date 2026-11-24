## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `hubspot__engagement_calls`, the output changes. |

Not checked: `CHANGELOG.md` (documentation)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `fa630cc4f0cb` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `integration_tests/dbt_project.yml`, `macros/engagements_joined.sql`. dbt project: changed `hubspot__engagement_calls`, `hubspot__engagement_emails`, `hubspot__engagement_meetings`, `hubspot__engagement_notes`, `hubspot__engagement_tasks`; compared `hubspot__engagement_calls`, `hubspot__engagement_emails`, `hubspot__engagement_meetings`, `hubspot__engagement_notes`, `hubspot__engagement_tasks`; SQL on warehouse; tables `engagement_call_data` (engagement_call_data.csv), `engagement_data` (engagement_data.csv), `engagement_note_data` (engagement_note_data.csv), `engagement_contact_data` (engagement_contact_data.csv), `engagement_task_data` (engagement_task_data.csv), `engagement_deal_data` (engagement_deal_data.csv), `engagement_email_data` (engagement_email_data.csv), `engagement_company_data` (engagement_company_data.csv), `engagement_meeting_data` (engagement_meeting_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 274 comparable valid inputs give the same output |
| Not comparable | 1 valid inputs made the original fail too |
| Needs review | 22 of 25 inputs in review categories (inputs that break your dbt tests (stg_hubspot__engagement: not_null(engagement_id); stg_hubspot__engagement: unique(engagement_id); stg_hubspot__engagement_call: not_null(engagement_id); stg_hubspot__engagement_call: unique(engagement_id))) differ |

**Why:** the fix changes output on 274 valid inputs.

- Note: 1 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is tables as given, in `hubspot__engagement_calls`, the output changes.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If the file is sample as given, in `hubspot__engagement_calls`, the output changes.
  - case 001: `file-structure` input '<sample as given>' in `engagement_call_data` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If the input has another column layout (<extra column at the end>), in `hubspot__engagement_calls`, the output changes.
  - case 002: `schema` input '<extra column at the end>' in `engagement_call_data` (changed); input shrunk to the rows that show it
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If `_fivetran_synced` is 'a; "b"', in `hubspot__engagement_calls`, the output changes.
  - case 003: `delimiter-mix` input 'a; "b"' in `engagement_call_data._fivetran_synced` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If `disposition` is 'a; "b"', in `hubspot__engagement_calls`, the output changes.
  - case 004: `delimiter-mix` input 'a; "b"' in `engagement_call_data.disposition` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If `body` is 'a; "b"', in `hubspot__engagement_calls`, the output changes.
  - case 005: `delimiter-mix` input 'a; "b"' in `engagement_call_data.body` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If a value is 'a; "b" (in an added 'note' column)', in `hubspot__engagement_calls`, the output changes.
  - case 006: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `engagement_call_data` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...
- **Values change.** If `engagement_id` is the number 0, in `hubspot__engagement_calls`, the output changes.
  - case 007: `numeric-format` input '0' in `engagement_call_data.engagement_id` (changed)
  - hubspot__engagement_calls: header: [['_fivetran_synced', 'call_notes', 'callee_object_id', 'callee_object_type', 'disposition_id', 'call_duration_milliseconds', 'engagement_id', 'external_account_i...
  - hubspot__engagement_emails: header: [['_fivetran_synced', 'attached_video_id', 'was_attached_video_opened', 'was_attached_video_watched', 'email_send_event_created_timestamp', 'email_send_event_id'...

Proof ID `e54bc2cd53002b9d` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/hubspot@v0.5.2/out/integration_tests_dbt_project/proof.json`
