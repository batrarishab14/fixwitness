## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__balance_sheet`, the output has 380 rows instead of 475; the row for '2025-05-01' is missing. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `faf6a1aca674` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/dbt_project.yml` and 3 more. dbt project: changed `int_quickbooks__credit_card_pymt_double_entry`, `int_quickbooks__invoice_double_entry`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `credit_card_payment_txn_data` (credit_card_payment_txn_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 298 comparable valid inputs give the same output |
| Needs review | 2 of 2 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__credit_memo_line: not_null(credit_memo_id))) differ |

**Why:** the fix changes output on 298 valid inputs.

**What could go wrong:**

- **Rows added or lost.** If the file is tables as given, in `quickbooks__balance_sheet`, the output has 380 rows instead of 475; the row for '2025-05-01' is missing.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `id` is the number 0, in `quickbooks__balance_sheet`, the output has 0 rows instead of 95; the row for '2019-01-01' is missing.
  - case 001: `numeric-format` input '0' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If a `bill_payment_data` row has an empty `id`, in `quickbooks__balance_sheet`, the output has 0 rows instead of 95; the row for '2019-01-01' is missing.
  - case 002: `empty` input '' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `id` repeats the value of another row (23), in `quickbooks__balance_sheet`, the output has 0 rows instead of 95; the row for '2019-01-01' is missing.
  - case 003: `duplicate` input '23' in `bill_payment_data.id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `check_bank_account_id` is the number 0, in `quickbooks__balance_sheet`, the output has 0 rows instead of 95; the row for '2019-01-01' is missing.
  - case 004: `numeric-format` input '0' in `bill_payment_data.check_bank_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If a `bill_payment_data` row has an empty `check_bank_account_id`, in `quickbooks__balance_sheet`, the output has 380 rows instead of 475; the row for '2025-05-01' is missing.
  - case 005: `empty` input '' in `bill_payment_data.check_bank_account_id` (changed)
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `check_bank_account_id` repeats the value of another row (28), in `quickbooks__balance_sheet`, the output has 380 rows instead of 475; the row for '2025-05-01' is missing.
  - case 006: `duplicate` input '28' in `bill_payment_data.check_bank_account_id` (changed)
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If a `bill_payment_data` row has an empty `created_at`, in `quickbooks__balance_sheet`, the output has 380 rows instead of 475; the row for '2025-05-01' is missing.
  - case 007: `empty` input '' in `bill_payment_data.created_at` (changed)
  - quickbooks__balance_sheet: row count: 475 -> 380
  - quickbooks__balance_sheet: row 5, calendar_date: '2019-01-01' -> '2019-02-01'

Proof ID `fa222348bc784fb2` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.17.1/out/integration_tests_dbt_project/proof.json`
