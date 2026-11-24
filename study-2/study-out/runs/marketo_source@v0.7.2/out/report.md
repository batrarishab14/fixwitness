## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells). |

Not checked: `CHANGELOG.md` (documentation)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `2b66fcf69674` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `integration_tests/dbt_project.yml`, `models/stg_marketo.yml`, `models/stg_marketo__activity_click_email.sql` and 5 more. dbt project: changed `stg_marketo__activity_click_email`, `stg_marketo__activity_email_bounced`, `stg_marketo__activity_email_delivered`, `stg_marketo__activity_open_email`, `stg_marketo__activity_send_email`, `stg_marketo__activity_unsubscribe_email`; compared `stg_marketo__activity_click_email`, `stg_marketo__activity_email_bounced`, `stg_marketo__activity_email_delivered`, `stg_marketo__activity_open_email`, `stg_marketo__activity_send_email`, `stg_marketo__activity_unsubscribe_email`; SQL on warehouse; tables `marketo_activity_open_email_data` (marketo_activity_open_email_data.csv), `marketo_activity_email_delivered_data` (marketo_activity_email_delivered_data.csv), `marketo_activity_send_email_data` (marketo_activity_send_email_data.csv), `marketo_activity_click_email_data` (marketo_activity_click_email_data.csv), `marketo_activity_unsubscribe_email_data` (marketo_activity_unsubscribe_email_data.csv), `marketo_activity_email_bounced_data` (marketo_activity_email_bounced_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 256 comparable valid inputs give the same output |
| Not comparable | 19 valid inputs made the original fail too |
| Needs review | 7 of 25 inputs in review categories (inputs that break your dbt tests (stg_marketo__activity_click_email: unique(activity_id); stg_marketo__activity_email_bounced: unique(activity_id); stg_marketo__activity_email_delivered: unique(activity_id); stg_marketo__activity_open_email: not_null(activity_id))) differ |

**Why:** the fix changes output on 256 valid inputs.

- Note: 19 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is sample as given, in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 000: `file-structure` input '<sample as given>' in `marketo_activity_open_email_data` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If the input has another column layout (<extra column at the end>), in `stg_marketo__activity_open_email`, `email_send_id` for '2020-05-08T18:44:49' changes from 'ee05ad22cbf2d1646884ac4da1e45065' to '364b9a6757b1aa081bb2eb3ddffbf98d'.
  - case 001: `schema` input '<extra column at the end>' in `marketo_activity_open_email_data` (changed); input shrunk to the rows that show it
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If `device` is 'a; "b"', in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 003: `delimiter-mix` input 'a; "b"' in `marketo_activity_open_email_data.device` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If `platform` is 'a; "b"', in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 004: `delimiter-mix` input 'a; "b"' in `marketo_activity_open_email_data.platform` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If `primary_attribute_value` is 'a; "b"', in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 005: `delimiter-mix` input 'a; "b"' in `marketo_activity_open_email_data.primary_attribute_value` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If `user_agent` is 'a; "b"', in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 006: `delimiter-mix` input 'a; "b"' in `marketo_activity_open_email_data.user_agent` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If a value is 'a; "b" (in an added 'note' column)', in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 007: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `marketo_activity_open_email_data` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'
- **Values change.** If a `marketo_activity_open_email_data` row has an empty `activity_date`, in `stg_marketo__activity_click_email`, `email_send_id` changes from '7ec239d77f703060eecc5af7ea44629d' to '1a0490a7ced1c5bb301ff0b921820dee' (and 99 more cells).
  - case 008: `empty` input '' in `marketo_activity_open_email_data.activity_date` (changed)
  - stg_marketo__activity_click_email: row 1, email_send_id: '7ec239d77f703060eecc5af7ea44629d' -> '1a0490a7ced1c5bb301ff0b921820dee'
  - stg_marketo__activity_click_email: row 2, email_send_id: '37f7073b73d53de3480daa610a0628b0' -> '66abba846b6c050a135eb441dde060d1'

Proof ID `b767daf9a7c4e853` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/marketo_source@v0.7.2/out/integration_tests_dbt_project/proof.json`
