## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__general_ledger`, column `transaction_id` disappears. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `f97031a1548c` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 3 more. dbt project: changed `quickbooks__general_ledger`; compared `quickbooks__balance_sheet`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 269 comparable valid inputs give the same output |
| Needs review | 31 of 31 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__account: not_null(account_id); stg_quickbooks__account: unique(account_id); stg_quickbooks__bill_line: not_null(bill_id); stg_quickbooks__bill_payment_line: not_null(bill_payment_id))) differ |

**Why:** the fix changes output on 269 valid inputs.

**What could go wrong:**

- **Values change.** If the file is tables as given, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If `id` is the number 0, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 001: `numeric-format` input '0' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If a `bill_payment_data` row has an empty `id`, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 002: `empty` input '' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If `id` repeats the value of another row (23), in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 003: `duplicate` input '23' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If `check_bank_account_id` is the number 0, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 004: `numeric-format` input '0' in `bill_payment_data.check_bank_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If a `bill_payment_data` row has an empty `check_bank_account_id`, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 005: `empty` input '' in `bill_payment_data.check_bank_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If `check_bank_account_id` repeats the value of another row (28), in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 006: `duplicate` input '28' in `bill_payment_data.check_bank_account_id` (changed)
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...
- **Values change.** If a `bill_payment_data` row has an empty `credit_card_account_id`, in `quickbooks__general_ledger`, column `transaction_id` disappears.
  - case 007: `empty` input '' in `bill_payment_data.credit_card_account_id` (changed)
  - quickbooks__general_ledger: header: [['unique_id', 'transaction_id', 'transaction_index', 'transaction_date', 'customer_id', 'vendor_id', 'amount', 'account_id', 'account_number', 'account_name', '...

Proof ID `6f018058bd08db22` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.5.2/out/integration_tests_dbt_project/proof.json`
