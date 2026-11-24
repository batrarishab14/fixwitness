## fixwitness: INCONCLUSIVE (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |
| `.buildkite/scripts/run_models.sh` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_zuora/.buildkite/scripts; pass one with --sample |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `32c46adcb73e` (original) vs working tree (fix); changed: `.buildkite/scripts/run_models.sh`, `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html` and 16 more. dbt project: changed `int_zuora__account_enriched`, `int_zuora__transactions_grouped`, `zuora__billing_history`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; compared `zuora__account_daily_overview`, `zuora__account_overview`, `zuora__billing_history`, `zuora__line_item_history`, `zuora__monthly_recurring_revenue`, `zuora__subscription_overview`; SQL on warehouse; tables `zuora_taxation_item_data` (zuora_taxation_item_data.csv), `zuora_credit_balance_adjustment_data` (zuora_credit_balance_adjustment_data.csv), `zuora_subscription_data` (zuora_subscription_data.csv), `zuora_product_rate_plan_data` (zuora_product_rate_plan_data.csv), `zuora_invoice_data` (zuora_invoice_data.csv), `zuora_payment_method_data` (zuora_payment_method_data.csv), `zuora_amendment_data` (zuora_amendment_data.csv), `zuora_invoice_payment_data` (zuora_invoice_payment_data.csv), `zuora_rate_plan_charge_data` (zuora_rate_plan_charge_data.csv), `zuora_payment_data` (zuora_payment_data.csv), `zuora_invoice_item_data` (zuora_invoice_item_data.csv), `zuora_contact_data` (zuora_contact_data.csv), `zuora_product_rate_plan_charge_data` (zuora_product_rate_plan_charge_data.csv), `zuora_account_data` (zuora_account_data.csv), `zuora_product_data` (zuora_product_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 300 valid inputs made the original fail too |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: value ' ' in zuora_payment_method_data.credit_card_country is not an integer
- Note: 300 valid inputs could not be compared because the original failed on them

Proof ID `06a502cc3f6a5508` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/zuora@v0.3.2/out/integration_tests_dbt_project/proof.json`
