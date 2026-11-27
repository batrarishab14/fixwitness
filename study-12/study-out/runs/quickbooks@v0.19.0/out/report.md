## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__balance_sheet`, `converted_amount` changes from -349998 to -255762 (and 145 more cells). |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `dfc8f6836105` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 2 more. dbt project: changed `int_quickbooks__bill_payment_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `bill_linked_txn_data` (bill_linked_txn_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 70 of 292 comparable valid inputs give the same output |
| Needs review | 6 of 8 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__bill_line: not_null(bill_id); stg_quickbooks__bill_linked_txn: not_null(bill_id); stg_quickbooks__bill_payment_line: not_null(bill_payment_id); stg_quickbooks__journal_entry_line: not_null(journal_entry_id))) differ |

**Why:** the fix changes output on 222 valid inputs.

**What could go wrong:**

- **Numbers change.** If the file is tables as given, in `quickbooks__balance_sheet`, `converted_amount` changes from -349998 to -255762 (and 145 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__balance_sheet: row 183, converted_amount: '-349998' -> '-255762'
  - quickbooks__balance_sheet: row 184, converted_amount: '-349998' -> '-255762'
- **Numbers change.** If `amount` is the number 0, in `quickbooks__general_ledger`, `adjusted_converted_amount` for '719ecd73cc8df8f1671421eec0b2d0c0' changes from -96136 to -50000 (and 3 more cells).
  - case 051: `numeric-format` input '0' in `credit_memo_line_data.amount` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 183, converted_amount: '-349998' -> '-255762'
  - quickbooks__balance_sheet: row 184, converted_amount: '-349998' -> '-255762'
- **Numbers change.** If a `credit_memo_line_data` row has an empty `amount`, in `quickbooks__balance_sheet`, `converted_amount` changes from -531680 to -439408 (and 221 more cells).
  - case 052: `empty` input '' in `credit_memo_line_data.amount` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row 183, converted_amount: '-349998' -> '-255762'
  - quickbooks__balance_sheet: row 184, converted_amount: '-349998' -> '-255762'
- **Numbers change.** If `amount` repeats the value of another row (0), in `quickbooks__balance_sheet`, `converted_amount` changes from -349998 to -255762 (and 145 more cells).
  - case 053: `duplicate` input '0' in `credit_memo_line_data.amount` (changed)
  - quickbooks__balance_sheet: row 183, converted_amount: '-349998' -> '-255762'
  - quickbooks__balance_sheet: row 184, converted_amount: '-349998' -> '-255762'
- **Numbers change.** If every `amount` in `credit_memo_line_data` is empty (NULL), in `quickbooks__balance_sheet`, `converted_amount` changes from -349998 to -255762 (and 145 more cells).
  - case 054: `null-column` input '<all NULL>' in `credit_memo_line_data.amount` (changed)
  - quickbooks__balance_sheet: row 183, converted_amount: '-349998' -> '-255762'
  - quickbooks__balance_sheet: row 184, converted_amount: '-349998' -> '-255762'
- **Numbers change.** If `id` is the number 0, in `quickbooks__general_ledger`, `running_converted_balance` for '0f0cc8ee8484569bf24060e15f43d4a5' changes from -516033 to -421797 (and 29 more cells).
  - case 055: `numeric-format` input '0' in `account_data.id` (changed)
  - quickbooks__general_ledger: row 2, running_converted_balance: '-516033' -> '-421797'
  - quickbooks__general_ledger: row 3, running_converted_balance: '-519533' -> '-425297'
- **Numbers change.** If an `account_data` row has an empty `id`, in `quickbooks__general_ledger`, `running_converted_balance` for '0f0cc8ee8484569bf24060e15f43d4a5' changes from -516033 to -421797 (and 29 more cells).
  - case 056: `empty` input '' in `account_data.id` (changed)
  - quickbooks__general_ledger: row 2, running_converted_balance: '-516033' -> '-421797'
  - quickbooks__general_ledger: row 3, running_converted_balance: '-519533' -> '-425297'
- **Numbers change.** If `id` repeats the value of another row (52), in `quickbooks__general_ledger`, `running_converted_balance` for '0f0cc8ee8484569bf24060e15f43d4a5' changes from -516033 to -421797 (and 29 more cells).
  - case 057: `duplicate` input '52' in `account_data.id` (changed)
  - quickbooks__general_ledger: row 2, running_converted_balance: '-516033' -> '-421797'
  - quickbooks__general_ledger: row 3, running_converted_balance: '-519533' -> '-425297'

Proof ID `e300f20ce4413f2c` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.19.0/out/integration_tests_dbt_project/proof.json`
