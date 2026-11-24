## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `dfc8f6836105` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 2 more. dbt project: changed `int_quickbooks__bill_payment_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `bill_linked_txn_data` (bill_linked_txn_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 292 valid inputs made the original fail too |
| Needs review | 0 of 8 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__bill_line: not_null(bill_id); stg_quickbooks__bill_linked_txn: not_null(bill_id); stg_quickbooks__bill_payment_line: not_null(bill_payment_id); stg_quickbooks__journal_entry_line: not_null(journal_entry_id))) differ |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: table deposit_data has an empty or repeated column name
- Note: 292 valid inputs could not be compared because the original failed on them

Proof ID `3a15e8a541bdc071` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.19.0/out/integration_tests_dbt_project/proof.json`
