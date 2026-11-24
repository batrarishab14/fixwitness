## fixwitness: FAIL (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing. |
| `.buildkite/scripts/run_models.sh` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_fivetran_log/.buildkite/scripts; pass one with --sample |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `cef651a48388` (original) vs working tree (fix); changed: `.buildkite/scripts/run_models.sh`, `.quickstart/quickstart.yml`, `CHANGELOG.md`, `README.md`, `dbt_project.yml` and 6 more. dbt project: changed `fivetran_platform__audit_table`; compared `fivetran_platform__audit_table`; SQL on warehouse; tables `connection` (connection.csv), `destination` (destination.csv), `log` (log.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 49 of 291 comparable valid inputs give the same output |
| Needs review | 9 of 9 inputs in review categories (inputs that break your dbt tests (stg_fivetran_platform__destination: not_null(destination_id); stg_fivetran_platform__destination: unique(destination_id))) differ |

**Why:** the fix changes output on 242 valid inputs.

**What could go wrong:**

- **Rows added or lost.** If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 000: `file-structure` input '<sample as given>' in `connection` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If the input has another column layout (<extra column at the end>), in `fivetran_platform__audit_table`, the output has 1 row instead of 0; a new row for 'this_connection' appears.
  - case 001: `schema` input '<extra column at the end>' in `connection` (changed); input shrunk to the rows that show it
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `connection_id` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 6 rows instead of 8; the row for 'this_connection' is missing.
  - case 002: `delimiter-mix` input 'a; "b"' in `connection.connection_id` (changed)
  - fivetran_platform__audit_table: row count: 8 -> 6
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `connecting_user_id` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 003: `delimiter-mix` input 'a; "b"' in `connection.connecting_user_id` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `connection_name` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 004: `delimiter-mix` input 'a; "b"' in `connection.connection_name` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, schema_name: 'a; "b"' -> 'instagram_business'
- **Rows added or lost.** If `connector_type` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 005: `delimiter-mix` input 'a; "b"' in `connection.connector_type` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `destination_id` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 6 rows instead of 8; the row for 'this_connection' is missing.
  - case 006: `delimiter-mix` input 'a; "b"' in `connection.destination_id` (changed)
  - fivetran_platform__audit_table: row count: 8 -> 6
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If a value is 'a; "b" (in an added 'note' column)', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 007: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `connection` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'

Proof ID `8d8885fe5031ea32` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/fivetran_log@v2.4.0-a1/out/integration_tests_dbt_project/proof.json`
