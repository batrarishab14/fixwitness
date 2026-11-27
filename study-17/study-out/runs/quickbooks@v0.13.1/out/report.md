## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `e604697a5188` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `docs/run_results.json` and 3 more. dbt project: changed `quickbooks__profit_and_loss`; compared `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 288 comparable valid inputs give the same output |
| Not comparable | 3 valid inputs made the original fail too |
| Needs review | 9 of 9 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__account: accepted_values(classification))) differ |

**Why:** the fix changes output on 288 valid inputs.

- Note: 3 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is tables as given, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If a `bill_payment_data` row has an empty `payable_account_id`, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 001: `empty` input '' in `bill_payment_data.payable_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `payable_account_id` repeats the value of another row (''), in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 002: `duplicate` input '' in `bill_payment_data.payable_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `total_amount` is the number 0, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 003: `numeric-format` input '0' in `bill_payment_data.total_amount` (changed); input shrunk to the rows that show it
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `total_amount` has extra spaces (' 42 '), in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 004: `whitespace` input ' 42 ' in `bill_payment_data.total_amount` (changed); input shrunk to the rows that show it
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If a `bill_payment_data` row has an empty `total_amount`, in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 005: `empty` input '' in `bill_payment_data.total_amount` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If `total_amount` repeats the value of another row (''), in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 006: `duplicate` input '' in `bill_payment_data.total_amount` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...
- **Values change.** If every `payable_account_id` in `bill_payment_data` is empty (NULL), in `quickbooks__profit_and_loss`, columns `period_first_day`, `period_last_day` disappear.
  - case 007: `null-column` input '<all NULL>' in `bill_payment_data.payable_account_id` (changed)
  - quickbooks__profit_and_loss: header: [['calendar_date', 'period_first_day', 'period_last_day', 'source_relation', 'account_class', 'class_id', 'is_sub_account', 'parent_account_number', 'parent_acc...

Proof ID `fbc9d87d151900cc` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.13.1/out/integration_tests_dbt_project/proof.json`
