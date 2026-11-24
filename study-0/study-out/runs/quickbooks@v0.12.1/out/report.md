## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code); `integration_tests/.gitignore` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `d74221ddcbe5` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 8 more. dbt project: changed `int_quickbooks__bill_payment_double_entry`, `int_quickbooks__credit_memo_double_entry`, `int_quickbooks__deposit_double_entry`, `int_quickbooks__invoice_double_entry`, `int_quickbooks__payment_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 287 comparable valid inputs give the same output |
| Not comparable | 10 valid inputs made the original fail too |
| Needs review | 3 of 3 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__credit_memo_line: not_null(credit_memo_id); stg_quickbooks__journal_entry_line: accepted_values(posting_type))) differ |

**Why:** the fix changes output on 287 valid inputs.

- Note: 10 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Rows added or lost.** If the file is tables as given, in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If the file is sample as given, in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 001: `file-structure` input '<sample as given>' in `bill_payment_data` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If the input has another column layout (<extra column at the end>), in `quickbooks__general_ledger`, the output has 0 rows instead of 6; the row for '26d45571f7857aabbe4872248eb32220' is missing.
  - case 002: `schema` input '<extra column at the end>' in `bill_payment_data` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `check_print_status` is 'a; "b"', in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 003: `delimiter-mix` input 'a; "b"' in `bill_payment_data.check_print_status` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `currency_id` is 'a; "b"', in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 004: `delimiter-mix` input 'a; "b"' in `bill_payment_data.currency_id` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `pay_type` is 'a; "b"', in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 005: `delimiter-mix` input 'a; "b"' in `bill_payment_data.pay_type` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If a value is 'a; "b" (in an added 'note' column)', in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 006: `delimiter-mix` input 'a; "b" (in an added \'note\' column)' in `bill_payment_data` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'
- **Rows added or lost.** If `id` is the number 0, in `quickbooks__balance_sheet`, the output has 285 rows instead of 380; the row for '2024-12-01' is missing.
  - case 007: `numeric-format` input '0' in `bill_payment_data.id` (changed)
  - quickbooks__balance_sheet: row count: 380 -> 285
  - quickbooks__balance_sheet: row 4, calendar_date: '2019-01-01' -> '2019-02-01'

Proof ID `46868ccd1c890765` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.12.1/out/integration_tests_dbt_project/proof.json`
