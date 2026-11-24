## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `e604697a5188` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `docs/run_results.json` and 3 more. dbt project: changed `quickbooks__profit_and_loss`; compared `quickbooks__profit_and_loss`; SQL on warehouse; tables `account_data` (account_data.csv), `purchase_line_data` (purchase_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `transfer_data` (transfer_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `deposit_line_data` (deposit_line_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `payment_data` (payment_data.csv), `journal_entry_data` (journal_entry_data.csv), `bill_line_data` (bill_line_data.csv), `bill_data` (bill_data.csv), `credit_memo_data` (credit_memo_data.csv), `bill_payment_data` (bill_payment_data.csv), `item_data` (item_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `purchase_data` (purchase_data.csv), `bundle_item_data` (bundle_item_data.csv), `invoice_data` (invoice_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `invoice_line_data` (invoice_line_data.csv), `payment_line_data` (payment_line_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 278 comparable valid inputs give the same output |
| Not comparable | 8 valid inputs made the original fail too |
| Needs review | 14 of 14 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__account: accepted_values(classification); stg_quickbooks__account: not_null(account_id); stg_quickbooks__journal_entry_line: accepted_values(posting_type); stg_quickbooks__purchase_line: not_null(purchase_id))) differ |

**Why:** the fix changes output on 278 valid inputs.

- Note: 8 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is tables as given, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If the file is sample as given, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 001: `file-structure` input '<sample as given>' in `account_data` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If the input has another column layout (<extra column at the end>), in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 002: `schema` input '<extra column at the end>' in `account_data` (changed); input shrunk to the rows that show it
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `account_sub_type` is 'a; "b"', in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 003: `delimiter-mix` input 'a; "b"' in `account_data.account_sub_type` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `account_type` is 'a; "b"', in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 004: `delimiter-mix` input 'a; "b"' in `account_data.account_type` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `currency_id` is 'a; "b"', in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 006: `delimiter-mix` input 'a; "b"' in `account_data.currency_id` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `fully_qualified_name` is 'a; "b"', in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 007: `delimiter-mix` input 'a; "b"' in `account_data.fully_qualified_name` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `name` is 'a; "b"', in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 008: `delimiter-mix` input 'a; "b"' in `account_data.name` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...

Proof ID `66a92e3cd7027de5` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.13.1/out/integration_tests_dbt_project/proof.json`
