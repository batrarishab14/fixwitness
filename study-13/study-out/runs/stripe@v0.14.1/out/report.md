## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `quantity` is the number 0, the fix fails (fixwitness.sqlrun: query failed: DivisionByZero: division by zero) while the original runs. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `e2677a51f24d` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/dbt_project.yml` and 3 more. dbt project: changed `stripe__line_item_enhanced`; compared `stripe__line_item_enhanced`; SQL on warehouse; tables `fee_data` (fee_data.csv), `account_data` (account_data.csv), `balance_transaction_data` (balance_transaction_data.csv), `price_data` (price_data.csv), `customer_data` (customer_data.csv), `payment_intent_data` (payment_intent_data.csv), `refund_data` (refund_data.csv), `payment_method_data` (payment_method_data.csv), `invoice_data` (invoice_data.csv), `product_data` (product_data.csv), `discount_data_postgres` (discount_data_postgres.csv), `charge_data` (charge_data.csv), `subscription_history_data` (subscription_history_data.csv), `invoice_line_item_data` (invoice_line_item_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 291 of 292 comparable valid inputs give the same output |
| Needs review | 0 of 8 inputs in review categories (inputs that break your dbt tests (stg_stripe__account: not_null(account_id); stg_stripe__balance_transaction: not_null(balance_transaction_id); stg_stripe__fee: not_null(balance_transaction_id); stg_stripe__refund: not_null(refund_id))) differ |

**Why:** the fix changes output on 1 valid inputs.

**What could go wrong:**

- **The job fails.** If `quantity` is the number 0, the fix fails (fixwitness.sqlrun: query failed: DivisionByZero: division by zero) while the original runs.
  - case 296: `numeric-format` input '0' in `invoice_line_item_data.quantity` (after-failed); input shrunk to the rows that show it
  - the fix failed where the original worked: fixwitness.sqlrun: query failed: DivisionByZero: division by zero

Proof ID `2f4697839e0cfd87` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/stripe@v0.14.1/out/integration_tests_dbt_project/proof.json`
