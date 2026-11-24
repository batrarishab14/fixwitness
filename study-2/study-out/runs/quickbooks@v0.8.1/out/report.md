## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__balance_sheet`, `amount` changes from 57682 to 0 (and 476 more cells). |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `db94c2542b8e` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `docs/run_results.json` and 3 more. dbt project: changed `int_quickbooks__general_ledger_balances`, `quickbooks__general_ledger`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 291 comparable valid inputs give the same output |
| Needs review | 9 of 9 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__account: accepted_values(classification))) differ |

**Why:** the fix changes output on 291 valid inputs.

**What could go wrong:**

- **Numbers change.** If the file is tables as given, in `quickbooks__balance_sheet`, `amount` changes from 57682 to 0 (and 476 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If `transaction_date` is the date '2026-01-01', in `quickbooks__general_ledger_by_period`, `period_net_change` changes from -25 to 0 (and 1 more cell).
  - case 001: `date-format` input '2026-01-01' in `bill_payment_data.transaction_date` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If a `bill_payment_data` row has an empty `transaction_date`, in `quickbooks__general_ledger_by_period`, `period_net_change` changes from -25 to 0 (and 1 more cell).
  - case 002: `empty` input '' in `bill_payment_data.transaction_date` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If `transaction_date` repeats the value of another row (''), in `quickbooks__general_ledger_by_period`, `period_net_change` changes from -25 to 0 (and 1 more cell).
  - case 003: `duplicate` input '' in `bill_payment_data.transaction_date` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If `vendor_id` is the number 0, in `quickbooks__general_ledger_by_period`, `period_net_change` changes from -825 to 0 (and 5 more cells).
  - case 004: `numeric-format` input '0' in `bill_payment_data.vendor_id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If `vendor_id` has extra spaces (' 42 '), in `quickbooks__balance_sheet`, `amount` changes from 57682 to 0 (and 476 more cells).
  - case 005: `whitespace` input ' 42 ' in `bill_payment_data.vendor_id` (changed)
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If a `bill_payment_data` row has an empty `vendor_id`, in `quickbooks__balance_sheet`, `amount` changes from 57682 to 0 (and 476 more cells).
  - case 006: `empty` input '' in `bill_payment_data.vendor_id` (changed)
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'
- **Numbers change.** If `vendor_id` repeats the value of another row (''), in `quickbooks__balance_sheet`, `amount` changes from 57682 to 0 (and 476 more cells).
  - case 007: `duplicate` input '' in `bill_payment_data.vendor_id` (changed)
  - quickbooks__balance_sheet: row 3, amount: '57682' -> '0'
  - quickbooks__balance_sheet: row 9, amount: '57682' -> '0'

Proof ID `cf3626d2e5253714` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.8.1/out/integration_tests_dbt_project/proof.json`
