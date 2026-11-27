## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `zuora__account_daily_overview`, `rolling_invoice_amount_paid` for '0017a2b901a41322fc81fcceb6aebc33' changes from 140.72 to 0 (and 675 more cells). |

Not checked: `.buildkite/scripts/run_models.sh` (CI configuration); `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `32c46adcb73e` (original) vs working tree (fix); changed: `.buildkite/scripts/run_models.sh`, `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html` and 16 more. dbt project: changed `int_zuora__account_enriched`, `int_zuora__transactions_grouped`, `zuora__billing_history`, `zuora__line_item_enhanced`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; compared `zuora__account_daily_overview`, `zuora__account_overview`, `zuora__billing_history`, `zuora__line_item_enhanced`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; SQL on warehouse; tables `zuora_taxation_item_data` (zuora_taxation_item_data.csv), `zuora_credit_balance_adjustment_data` (zuora_credit_balance_adjustment_data.csv), `zuora_rate_plan_data` (zuora_rate_plan_data.csv), `zuora_subscription_data` (zuora_subscription_data.csv), `zuora_product_rate_plan_data` (zuora_product_rate_plan_data.csv), `zuora_invoice_data` (zuora_invoice_data.csv), `zuora_payment_method_data` (zuora_payment_method_data.csv), `zuora_amendment_data` (zuora_amendment_data.csv), `zuora_invoice_payment_data` (zuora_invoice_payment_data.csv), `zuora_rate_plan_charge_data` (zuora_rate_plan_charge_data.csv), `zuora_payment_data` (zuora_payment_data.csv), `zuora_invoice_item_data` (zuora_invoice_item_data.csv), `zuora_contact_data` (zuora_contact_data.csv), `zuora_product_rate_plan_charge_data` (zuora_product_rate_plan_charge_data.csv), `zuora_account_data` (zuora_account_data.csv), `zuora_product_data` (zuora_product_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 300 comparable valid inputs give the same output |

**Why:** the fix changes output on 300 valid inputs.

**What could go wrong:**

- **Numbers change.** If the file is tables as given, in `zuora__account_daily_overview`, `rolling_invoice_amount_paid` for '0017a2b901a41322fc81fcceb6aebc33' changes from 140.72 to 0 (and 675 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '140.72' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '10.72' -> '0'
- **Numbers change.** If `balance` is the number 0, in `zuora__line_item_history`, `gross_revenue` for '2c92c0946763f3ca0167822990662f8a' changes from 0.0 to empty (and 1 more cell).
  - case 001: `numeric-format` input '0' in `zuora_taxation_item_data.balance` (changed); input shrunk to the rows that show it
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If a `zuora_taxation_item_data` row has an empty `created_date`, in `zuora__line_item_history`, `gross_revenue` for '2c92c0946763f3ca0167822990662f8a' changes from 0.0 to empty (and 1 more cell).
  - case 002: `empty` input '' in `zuora_taxation_item_data.created_date` (changed); input shrunk to the rows that show it
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If `created_date` repeats the value of another row ('2016-01-15 16:42:00.000000'), in `zuora__line_item_history`, `gross_revenue` for '2c92c0946763f3ca0167822990662f8a' changes from 0.0 to empty (and 1 more cell).
  - case 003: `duplicate` input '2016-01-15 16:42:00.000000' in `zuora_taxation_item_data.created_date` (changed); input shrunk to the rows that show it
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If two `zuora_taxation_item_data` rows of the same group have `created_date` = '2016-01-15 23:03:00.000000' and '2016-01-15 23:03:00.000000', in `zuora__line_item_history`, `gross_revenue` for '2c92c0946763f3ca01678229905f2f7d' changes from 0.0 to empty (and 9 more cells).
  - case 004: `pairs` input '2016-01-15 23:03:00.000000 | 2016-01-15 23:03:00.000000' in `zuora_taxation_item_data.created_date` (changed); input shrunk to the rows that show it
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If a `zuora_taxation_item_data` row has an empty `exchange_rate_date`, in `zuora__account_daily_overview`, `rolling_invoice_amount_paid` for '0051f0280b39b544b9ee4650952674f4' changes from 70.36 to 0 (and 1227 more cells).
  - case 005: `empty` input '' in `zuora_taxation_item_data.exchange_rate_date` (changed)
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If `exchange_rate_date` repeats the value of another row (''), in `zuora__account_daily_overview`, `rolling_invoice_amount_paid` for '0051f0280b39b544b9ee4650952674f4' changes from 70.36 to 0 (and 1227 more cells).
  - case 006: `duplicate` input '' in `zuora_taxation_item_data.exchange_rate_date` (changed)
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'
- **Numbers change.** If two `zuora_taxation_item_data` rows of the same group have `exchange_rate_date` = '2015-03-01 00:00:00.000000' and '2015-03-01 00:00:00.000000', in `zuora__account_daily_overview`, `rolling_invoice_amount_paid` for '0051f0280b39b544b9ee4650952674f4' changes from 70.36 to 0 (and 1227 more cells).
  - case 007: `pairs` input '2015-03-01 00:00:00.000000 | 2015-03-01 00:00:00.000000' in `zuora_taxation_item_data.exchange_rate_date` (changed)
  - zuora__account_daily_overview: row 1, rolling_invoice_amount_paid: '70.36' -> '0'
  - zuora__account_daily_overview: row 1, rolling_tax_amount: '5.36' -> '0'

Proof ID `c0498a44dba6723b` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/zuora@v0.3.2/out/integration_tests_dbt_project/proof.json`
