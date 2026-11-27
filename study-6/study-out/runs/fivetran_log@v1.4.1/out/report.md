## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `message_data` is 'a; "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs. |

Not checked: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `be9ee6b7fdb0` (original) vs working tree (fix); changed: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md`, `.github/workflows/auto-release.yml`, `.quickstart/quickstart.yml`, `CHANGELOG.md`, `dbt_project.yml` and 6 more. dbt project: changed `fivetran_platform__audit_user_activity`; compared `fivetran_platform__audit_user_activity`; SQL on warehouse; tables `connector` (connector.csv), `destination` (destination.csv), `destination_membership` (destination_membership.csv), `user` (user.csv), `log` (log.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 258 of 265 comparable valid inputs give the same output |
| Needs review | 0 of 35 inputs in review categories (inputs that break your dbt tests (stg_fivetran_platform__destination: not_null(destination_id); stg_fivetran_platform__destination: unique(destination_id); stg_fivetran_platform__destination_membership: unique_combination_of_columns(destination_id, user_id); stg_fivetran_platform__log: unique_combination_of_columns(log_id, created_at))) differ |

**Why:** the fix changes output on 7 valid inputs.

**What could go wrong:**

- **The job fails.** If `message_data` is 'a; "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 242: `delimiter-mix` input 'a; "b"' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is 'Ünïcødé', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 271: `unicode` input 'Ünïcødé' in `log.message_data` (after-failed); input shrunk to the rows that show it
  - CONTEXT:  JSON data, line 1: Ünïcødé
- **The job fails.** If `message_data` is 'north-east', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 272: `punctuation` input 'north-east' in `log.message_data` (after-failed); input shrunk to the rows that show it
  - CONTEXT:  JSON data, line 1: north...
- **The job fails.** If `message_data` is 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 273: `long` input 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...' in `log.message_data` (after-failed); input shrunk to the rows that show it
  - CONTEXT:  JSON data, line 1: ...xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- **The job fails.** If `message_data` is 'comma, inside', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 274: `csv-structure` input 'comma, inside' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: comma...
- **The job fails.** If `message_data` is 'O'Brien', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 275: `quotes` input "O'Brien" in `log.message_data` (after-failed); input shrunk to the rows that show it
  - CONTEXT:  JSON data, line 1: O...
- **The job fails.** If `message_data` is '*', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 277: `shell-metachar` input '*' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: *

Proof ID `d0aff002eb354cd6` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/fivetran_log@v1.4.1/out/integration_tests_dbt_project/proof.json`
