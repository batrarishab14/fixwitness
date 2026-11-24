## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells). |

Not checked: `.gitignore` (not code); `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code); `integration_tests/requirements.txt` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `6864ac3e60f1` (original) vs working tree (fix); changed: `.gitignore`, `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json` and 7 more. dbt project: changed `fivetran_platform__audit_table`; compared `fivetran_platform__audit_table`; SQL on warehouse; tables `connector` (connector.csv), `destination` (destination.csv), `log` (log.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 56 of 288 comparable valid inputs give the same output |
| Needs review | 9 of 12 inputs in review categories (inputs that break your dbt tests (stg_fivetran_platform__destination: not_null(destination_id); stg_fivetran_platform__destination: unique(destination_id); stg_fivetran_platform__log: unique_combination_of_columns(log_id, created_at))) differ |

**Why:** the fix changes output on 232 valid inputs.

**What could go wrong:**

- **Values change.** If the file is sample as given, in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells).
  - case 000: `file-structure` input '<sample as given>' in `connector` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'
- **Values change.** If the input has another column layout (<extra column at the end>), in `fivetran_platform__audit_table`, `unique_table_sync_key` for 'intrinsic_departed' changes from 'd3c8a788662a6838843f04047d7d06e9' to 'a26d7efa3e1149bcf76cd582cfa8397d'.
  - case 001: `schema` input '<extra column at the end>' in `connector` (changed); input shrunk to the rows that show it
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'
- **Values change.** If `connector_id` is 'a; "b"', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from '83ebf1a920fc9bc1c18befedefdd2b12' to 'a26d7efa3e1149bcf76cd582cfa8397d' (and 5 more cells).
  - case 002: `delimiter-mix` input 'a; "b"' in `connector.connector_id` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: '83ebf1a920fc9bc1c18befedefdd2b12' -> 'a26d7efa3e1149bcf76cd582cfa8397d'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '9dd940a2492c9cbdd1bfdff47f49e5f3' -> '12bab09eed9bba93b782815db508df51'
- **Values change.** If `connecting_user_id` is 'a; "b"', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells).
  - case 003: `delimiter-mix` input 'a; "b"' in `connector.connecting_user_id` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'
- **Values change.** If `connector_name` is 'a; "b"', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells).
  - case 004: `delimiter-mix` input 'a; "b"' in `connector.connector_name` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'
- **Values change.** If `connector_type` is 'a; "b"', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells).
  - case 005: `delimiter-mix` input 'a; "b"' in `connector.connector_type` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'
- **Values change.** If `destination_id` is 'a; "b"', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from '83ebf1a920fc9bc1c18befedefdd2b12' to 'a26d7efa3e1149bcf76cd582cfa8397d' (and 5 more cells).
  - case 006: `delimiter-mix` input 'a; "b"' in `connector.destination_id` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: '83ebf1a920fc9bc1c18befedefdd2b12' -> 'a26d7efa3e1149bcf76cd582cfa8397d'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '9dd940a2492c9cbdd1bfdff47f49e5f3' -> '12bab09eed9bba93b782815db508df51'
- **Values change.** If a value is 'a; "b" (in an added 'note' column)', in `fivetran_platform__audit_table`, `unique_table_sync_key` changes from 'cdff13c70b5a69488f3697fc11f1ea10' to '6808881ca15f4b07b459a40598039791' (and 5 more cells).
  - case 007: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `connector` (changed)
  - fivetran_platform__audit_table: row 1, unique_table_sync_key: 'cdff13c70b5a69488f3697fc11f1ea10' -> '6808881ca15f4b07b459a40598039791'
  - fivetran_platform__audit_table: row 2, unique_table_sync_key: '843d505636dbf0ab906d8f941bf89fc2' -> '5fb92a0ce8dab35f4a5b506b7dec93cd'

Proof ID `710fbb6c23788c24` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/fivetran_log@v1.2.0/out/integration_tests_dbt_project/proof.json`
