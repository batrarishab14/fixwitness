## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `a1d4fbdaa701` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 11 more. dbt project: changed `int_zuora__account_enriched`; compared `zuora__account_daily_overview`, `zuora__account_overview`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; SQL on warehouse; tables `zuora_payment_method_data` (zuora_payment_method_data.csv), `zuora_invoice_item_data` (zuora_invoice_item_data.csv), `zuora_invoice_data` (zuora_invoice_data.csv), `zuora_account_data` (zuora_account_data.csv), `zuora_amendment_data` (zuora_amendment_data.csv), `zuora_subscription_data` (zuora_subscription_data.csv), `zuora_product_rate_plan_data` (zuora_product_rate_plan_data.csv), `zuora_payment_data` (zuora_payment_data.csv), `zuora_invoice_payment_data` (zuora_invoice_payment_data.csv), `zuora_credit_balance_adjustment_data` (zuora_credit_balance_adjustment_data.csv), `zuora_contact_data` (zuora_contact_data.csv), `zuora_product_rate_plan_charge_data` (zuora_product_rate_plan_charge_data.csv), `zuora_rate_plan_charge_data` (zuora_rate_plan_charge_data.csv), `zuora_taxation_item_data` (zuora_taxation_item_data.csv), `zuora_product_data` (zuora_product_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 300 valid inputs made the original fail too |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: value ' ' in zuora_payment_method_data.credit_card_country is not an integer
- Note: 300 valid inputs could not be compared because the original failed on them

Proof ID `b814d257539e7507` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/zuora@v0.4.0/out/integration_tests_dbt_project/proof.json`
