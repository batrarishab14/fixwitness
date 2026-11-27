## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `account_type` is 'Accounts Payable', in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears. |

Not checked: `.github/pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code); `integration_tests/.gitignore` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `76f324f566c8` (original) vs working tree (fix); changed: `.github/pull_request_template.md`, `.github/workflows/check_docs.yml`, `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json` and 10 more. dbt project: changed `int_quickbooks__bill_payment_double_entry`, `int_quickbooks__credit_memo_double_entry`, `int_quickbooks__deposit_double_entry`, `int_quickbooks__payment_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 282 of 285 comparable valid inputs give the same output |
| Needs review | 0 of 21 inputs in review categories () differ |

**Why:** the fix changes output on 3 valid inputs.

**What could go wrong:**

- **Rows added or lost.** If `account_type` is 'Accounts Payable', in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears.
  - case 301: `precondition` input 'Accounts Payable' in `account_data.account_type` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 570 -> 665
  - quickbooks__balance_sheet: row 7, calendar_date: '2019-02-01' -> '2019-01-01'
- **Rows added or lost.** If `account_type` is 'Accounts Receivable', in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears.
  - case 303: `precondition` input 'Accounts Receivable' in `account_data.account_type` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 570 -> 665
  - quickbooks__balance_sheet: row 4, account_class: 'Equity' -> 'Asset'
- **Rows added or lost.** If `account_sub_type` is 'UndepositedFunds', in `quickbooks__general_ledger`, the output has 4 rows instead of 0; a new row for '34b10b3ac069df90bdfdd7870f43b7ac' appears.
  - case 305: `precondition` input 'UndepositedFunds' in `account_data.account_sub_type` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 88, amount: '0.0' -> '-97222.0'
  - quickbooks__balance_sheet: row 94, amount: '0.0' -> '-97222.0'

Proof ID `c9c4e1f9f52aeaf2` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.5.3/out/integration_tests_dbt_project/proof.json`
