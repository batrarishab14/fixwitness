## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `currency_id` is written in another case ('usd'), in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `d6668e1256d3` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 23 more. dbt project: changed `int_quickbooks__credit_card_pymt_double_entry`, `quickbooks__expenses_sales_enhanced`, `quickbooks__general_ledger`, `stg_quickbooks__credit_card_payment_txn`, `stg_quickbooks__credit_card_payment_txn_tmp`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__expenses_sales_enhanced`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `bill_linked_txn_data` (bill_linked_txn_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `credit_card_payment_txn_data` (credit_card_payment_txn_data.csv), `payment_data` (payment_data.csv), `customer_data` (customer_data.csv), `payment_line_data` (payment_line_data.csv), `department_data` (department_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `vendor_data` (vendor_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 3 comparable valid inputs give the same output |
| Not comparable | 293 valid inputs made the original fail too |
| Needs review | 0 of 4 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__credit_memo_line: not_null(credit_memo_id); stg_quickbooks__journal_entry_line: accepted_values(posting_type))) differ |

**Why:** the fix changes output on 3 valid inputs.

- Note: the original failed on the sample itself: fixwitness.sqlrun: value '2021-01-01' in bill_data.doc_number is not an integer
- Note: 293 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Rows added or lost.** If `currency_id` is written in another case ('usd'), in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears.
  - case 254: `case` input 'usd' in `bill_data.currency_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row count: 120 -> 130
  - quickbooks__general_ledger: row 3, running_balance: '-233879' -> '-232591'
- **Rows added or lost.** If `currency_id` has extra spaces (' USD'), in `quickbooks__balance_sheet`, the output has 95 rows instead of 0; a new row for '2019-01-01' appears.
  - case 255: `whitespace` input ' USD' in `bill_data.currency_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row count: 120 -> 130
  - quickbooks__general_ledger: row 3, running_balance: '-233879' -> '-232591'
- **Rows added or lost.** If `updated_at` has extra spaces (' 2020-05-22 16:39:03'), in `quickbooks__general_ledger`, the output has 130 rows instead of 120; a new row for 'ee5cda0b2fdd7ffa12dbd7c97dc721bb' appears.
  - case 256: `whitespace` input ' 2020-05-22 16:39:03' in `bill_data.updated_at` (changed)
  - quickbooks__general_ledger: row count: 120 -> 130
  - quickbooks__general_ledger: row 3, running_balance: '-233879' -> '-232591'

Proof ID `bfc9d0b9c4cea034` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.18.1/out/integration_tests_dbt_project/proof.json`
