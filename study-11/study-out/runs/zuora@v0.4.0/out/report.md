## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 43 more cells). |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `a1d4fbdaa701` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 11 more. dbt project: changed `int_zuora__account_enriched`; compared `zuora__account_daily_overview`, `zuora__account_overview`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; SQL on warehouse; tables `zuora_taxation_item_data` (zuora_taxation_item_data.csv), `zuora_credit_balance_adjustment_data` (zuora_credit_balance_adjustment_data.csv), `zuora_subscription_data` (zuora_subscription_data.csv), `zuora_product_rate_plan_data` (zuora_product_rate_plan_data.csv), `zuora_invoice_data` (zuora_invoice_data.csv), `zuora_payment_method_data` (zuora_payment_method_data.csv), `zuora_amendment_data` (zuora_amendment_data.csv), `zuora_invoice_payment_data` (zuora_invoice_payment_data.csv), `zuora_rate_plan_charge_data` (zuora_rate_plan_charge_data.csv), `zuora_payment_data` (zuora_payment_data.csv), `zuora_invoice_item_data` (zuora_invoice_item_data.csv), `zuora_contact_data` (zuora_contact_data.csv), `zuora_product_rate_plan_charge_data` (zuora_product_rate_plan_charge_data.csv), `zuora_account_data` (zuora_account_data.csv), `zuora_product_data` (zuora_product_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 34 of 300 comparable valid inputs give the same output |

**Why:** the fix changes output on 266 valid inputs.

**What could go wrong:**

- **Values change.** If the file is tables as given, in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 43 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Values change.** If `account_id` is 'a; "b"', in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 129 more cells).
  - case 001: `delimiter-mix` input 'a; "b"' in `zuora_taxation_item_data.account_id` (changed)
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Rows added or lost.** If a `zuora_taxation_item_data` row has an empty `id`, in `zuora__account_overview`, the output has 1 row instead of 1.
  - case 002: `empty` input '' in `zuora_taxation_item_data.id` (changed); input shrunk to the rows that show it
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Rows added or lost.** If `id` repeats the value of another row ('dff38ac095012f19007b8a0942416110'), in `zuora__account_overview`, the output has 1 row instead of 1.
  - case 003: `duplicate` input 'dff38ac095012f19007b8a0942416110' in `zuora_taxation_item_data.id` (changed); input shrunk to the rows that show it
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Values change.** If two `zuora_taxation_item_data` rows of the same group have `id` = 'dff38ac03b24a6efd976ad1221ebd5cc' and 'DFF38AC03B24A6EFD976AD1221EBD5CC', in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 29 more cells).
  - case 004: `pairs` input 'dff38ac03b24a6efd976ad1221ebd5cc | DFF38AC03B24A6EFD976AD1221EBD5CC' in `zuora_taxation_item_data.id` (changed); input shrunk to the rows that show it
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Values change.** If a `zuora_taxation_item_data` row has an empty `account_id`, in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 129 more cells).
  - case 005: `empty` input '' in `zuora_taxation_item_data.account_id` (changed)
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Values change.** If `account_id` is 'north-east', in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 129 more cells).
  - case 006: `punctuation` input 'north-east' in `zuora_taxation_item_data.account_id` (changed)
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'
- **Values change.** If `account_id` is 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…', in `zuora__account_overview`, `account_id` changes from '2c92c0f967640caa0167836a3e396a3b' to empty (and 129 more cells).
  - case 007: `long` input 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...' in `zuora_taxation_item_data.account_id` (changed)
  - zuora__account_overview: row 1, account_id: '2c92c0f967640caa0167836a3e396a3b' -> ''
  - zuora__account_overview: row 1, account_created_at: '2018-12-06T12:07:17' -> '2016-01-15T16:00:35'

Proof ID `9be573179cdcadcd` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/zuora@v0.4.0/out/integration_tests_dbt_project/proof.json`
