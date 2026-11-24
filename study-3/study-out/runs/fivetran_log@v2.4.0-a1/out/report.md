## fixwitness: FAIL (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing. |
| `.buildkite/scripts/run_models.sh` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_fivetran_log/.buildkite/scripts; pass one with --sample |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.

---

### `integration_tests (dbt project)`


`integration_tests`: commit `cef651a48388` (original) vs working tree (fix); changed: `.buildkite/scripts/run_models.sh`, `.quickstart/quickstart.yml`, `CHANGELOG.md`, `README.md`, `dbt_project.yml` and 6 more. dbt project: changed `fivetran_platform__audit_table`; compared `fivetran_platform__audit_table`; SQL on warehouse; tables `destination` (destination.csv), `log` (log.csv), `connection` (connection.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 176 of 290 comparable valid inputs give the same output |
| Needs review | 10 of 10 inputs in review categories (inputs that break your dbt tests (stg_fivetran_platform__destination: not_null(destination_id); stg_fivetran_platform__destination: unique(destination_id))) differ |

**Why:** the fix changes output on 114 valid inputs.

**What could go wrong:**

- **Rows added or lost.** If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 000: `file-structure` input '<sample as given>' in `destination` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If the input has another column layout (<extra column at the end>), in `fivetran_platform__audit_table`, the output has 1 row instead of 0; a new row for 'this_connection' appears.
  - case 001: `schema` input '<extra column at the end>' in `destination` (changed); input shrunk to the rows that show it
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `id` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 6 rows instead of 8; the row for 'this_connection' is missing.
  - case 002: `delimiter-mix` input 'a; "b"' in `destination.id` (changed)
  - fivetran_platform__audit_table: row count: 8 -> 6
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `account_id` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 003: `delimiter-mix` input 'a; "b"' in `destination.account_id` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `name` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 004: `delimiter-mix` input 'a; "b"' in `destination.name` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `region` is 'a; "b"', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 005: `delimiter-mix` input 'a; "b"' in `destination.region` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If a value is 'a; "b" (in an added 'note' column)', in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing.
  - case 006: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `destination` (changed)
  - fivetran_platform__audit_table: row count: 16 -> 12
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'
- **Rows added or lost.** If `id` is 'Ünïcødé', in `fivetran_platform__audit_table`, the output has 6 rows instead of 8; the row for 'this_connection' is missing.
  - case 008: `unicode` input 'Ünïcødé' in `destination.id` (changed)
  - fivetran_platform__audit_table: row count: 8 -> 6
  - fivetran_platform__audit_table: row 1, write_to_table_end: '2021-12-09T14:26:51.703000' -> '2021-12-09T14:26:52.242000'

Proof ID `55fb608f015b521b` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/fivetran_log@v2.4.0-a1/out/integration_tests_dbt_project/proof.json`
