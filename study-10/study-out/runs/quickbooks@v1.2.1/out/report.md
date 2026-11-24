## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If every `currency_id` in `invoice_data` is empty (NULL), in `quickbooks__balance_sheet`, the output has 190 rows instead of 95; a new row for '2022-12-01' appears. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `integration_tests/requirements.txt` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `74ba053a2c70` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/dbt_project.yml` and 3 more. dbt project: changed `int_quickbooks__invoice_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 291 of 292 comparable valid inputs give the same output |
| Not comparable | 8 valid inputs made the original fail too |

**Why:** the fix changes output on 1 valid inputs.

- Note: 8 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Rows added or lost.** If every `currency_id` in `invoice_data` is empty (NULL), in `quickbooks__balance_sheet`, the output has 190 rows instead of 95; a new row for '2022-12-01' appears.
  - case 184: `null-column` input '<all NULL>' in `invoice_data.currency_id` (changed); input shrunk to the rows that show it
  - quickbooks__balance_sheet: row count: 855 -> 950
  - quickbooks__balance_sheet: row 7, account_class: 'Equity' -> 'Asset'

Proof ID `654df6f2c4980a30` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v1.2.1/out/integration_tests_dbt_project/proof.json`
