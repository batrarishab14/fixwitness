## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | not exercisable with this data: no input reaches what the change touched (column total_amount), so identical output proves nothing about it; add rows that have it |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `a492423f9aa8` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 4 more. dbt project: changed `int_quickbooks__purchase_transactions`; compared `quickbooks__expenses_sales_enhanced`; SQL on warehouse; tables `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `customer_data` (customer_data.csv), `department_data` (department_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_data` (invoice_line_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `vendor_data` (vendor_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | PASS: 296 of 296 comparable valid inputs give the same output |
| Needs review | 0 of 4 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__credit_memo_line: not_null(credit_memo_id); stg_quickbooks__purchase_line: not_null(purchase_id))) differ |

**Why:** not exercisable with this data: no input reaches what the change touched (column total_amount), so identical output proves nothing about it; add rows that have it.

Proof ID `d5de1529fc3d9f14` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.9.1/out/integration_tests_dbt_project/proof.json`
