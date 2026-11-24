## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `sales_item_account_id` is the number 0, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears. |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (new file: there is no original to compare)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `89242ebc2392` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 3 more. dbt project: changed `int_quickbooks__invoice_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 294 of 295 comparable valid inputs give the same output |
| Not comparable | 2 valid inputs made the original fail too |
| Needs review | 0 of 3 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__invoice_line: not_null(invoice_id); stg_quickbooks__invoice_line_bundle: not_null(invoice_id))) differ |

**Why:** the fix changes output on 1 valid inputs.

- Note: 2 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Rows added or lost.** If `sales_item_account_id` is the number 0, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears.
  - case 296: `numeric-format` input '0' in `invoice_line_data.sales_item_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row 50, unique_id: '8f18f7d13a295e62c1de44f39db8ebbf' -> '8f5c69aec6d38e5f33591c31e29f4582'
  - quickbooks__general_ledger: row 50, transaction_id: '40113' -> '228'

Proof ID `3c21a634fa466f70` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.15.0/out/integration_tests_dbt_project/proof.json`
