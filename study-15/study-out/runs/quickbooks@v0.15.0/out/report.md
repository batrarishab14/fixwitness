## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `sales_item_account_id` is the number 0, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears. |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (new file: there is no original to compare)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `89242ebc2392` (original) vs working tree (fix); changed: `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json` and 3 more. dbt project: changed `int_quickbooks__invoice_double_entry`; compared `quickbooks__balance_sheet`, `quickbooks__cash_flow_statement`, `quickbooks__general_ledger`, `quickbooks__general_ledger_by_period`, `quickbooks__profit_and_loss`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `credit_memo_line_data` (credit_memo_line_data.csv), `account_data` (account_data.csv), `vendor_credit_data` (vendor_credit_data.csv), `sales_receipt_line_data` (sales_receipt_line_data.csv), `deposit_data` (deposit_data.csv), `payment_data` (payment_data.csv), `payment_line_data` (payment_line_data.csv), `refund_receipt_data` (refund_receipt_data.csv), `bill_data` (bill_data.csv), `invoice_line_bundle_data` (invoice_line_bundle_data.csv), `invoice_line_data` (invoice_line_data.csv), `bundle_item_data` (bundle_item_data.csv), `purchase_line_data` (purchase_line_data.csv), `deposit_line_data` (deposit_line_data.csv), `invoice_data` (invoice_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `refund_receipt_line_data` (refund_receipt_line_data.csv), `journal_entry_line_data` (journal_entry_line_data.csv), `bill_line_data` (bill_line_data.csv), `purchase_data` (purchase_data.csv), `bundle_data` (bundle_data.csv), `sales_receipt_data` (sales_receipt_data.csv), `journal_entry_data` (journal_entry_data.csv), `credit_memo_data` (credit_memo_data.csv), `item_data` (item_data.csv), `vendor_credit_line_data` (vendor_credit_line_data.csv), `transfer_data` (transfer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 266 of 277 comparable valid inputs give the same output |
| Not comparable | 21 valid inputs made the original fail too |
| Needs review | 0 of 2 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__journal_entry_line: accepted_values(posting_type))) differ |

**Why:** the fix changes output on 11 valid inputs.

- Note: 21 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Rows added or lost.** If `sales_item_account_id` is the number 0, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears.
  - case 153: `numeric-format` input '0' in `invoice_line_data.sales_item_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row 50, unique_id: '8f18f7d13a295e62c1de44f39db8ebbf' -> '8f5c69aec6d38e5f33591c31e29f4582'
  - quickbooks__general_ledger: row 50, transaction_id: '40113' -> '228'
- **Rows added or lost.** If `sales_item_account_id` is the number -0, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears.
  - case 154: `numeric-format` input '-0' in `invoice_line_data.sales_item_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row 50, unique_id: '8f18f7d13a295e62c1de44f39db8ebbf' -> '8f5c69aec6d38e5f33591c31e29f4582'
  - quickbooks__general_ledger: row 50, transaction_id: '40113' -> '228'
- **Rows added or lost.** If `sales_item_account_id` is the number +7, in `quickbooks__general_ledger`, the output has 2 rows instead of 2; a new row for 'b10f9c3768cff317b67931b0f28ef563' appears.
  - case 155: `numeric-format` input '+7' in `invoice_line_data.sales_item_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row 11, running_balance: '-62814' -> '85253'
  - quickbooks__general_ledger: row 11, running_converted_balance: '-62814' -> '85253'
- **Values change.** If `sales_item_account_id` is the number -3, in `quickbooks__general_ledger`, `unique_id` changes from '9a3ff520f1ab763afe2df4fda96a6fc3' to 'aa0f26bc50dc3e38ea0149288bf80355' (and 31 more cells).
  - case 156: `numeric-format` input '-3' in `invoice_line_data.sales_item_account_id` (changed); input shrunk to the rows that show it
  - quickbooks__general_ledger: row 11, running_balance: '-62814' -> '85253'
  - quickbooks__general_ledger: row 11, running_converted_balance: '-62814' -> '85253'
- **Numbers change.** If `sales_item_account_id` is the number 10, in `quickbooks__general_ledger`, `running_balance` changes from -7282 to -8668 (and 428 more cells).
  - case 157: `numeric-format` input '10' in `invoice_line_data.sales_item_account_id` (changed)
  - quickbooks__general_ledger: row 54, running_balance: '-7282' -> '-8668'
  - quickbooks__general_ledger: row 54, running_converted_balance: '-7282' -> '-8668'
- **Values change.** If `sales_item_account_id` is the number 100, in `quickbooks__general_ledger`, `unique_id` changes from '6a6f9f1ec3050d8ae77d4ca502936dfa' to '6a6fb17beebafdf89c526b19ed9615e5' (and 665 more cells).
  - case 158: `numeric-format` input '100' in `invoice_line_data.sales_item_account_id` (changed)
  - quickbooks__general_ledger: row 31, unique_id: '6a6f9f1ec3050d8ae77d4ca502936dfa' -> '6a6fb17beebafdf89c526b19ed9615e5'
  - quickbooks__general_ledger: row 31, transaction_id: '40113' -> '2'
- **Values change.** If `sales_item_account_id` is the number 1200, in `quickbooks__general_ledger`, `unique_id` changes from '8f018a4280336d867e9dfdab85ff0d18' to '8f5c69aec6d38e5f33591c31e29f4582' (and 380 more cells).
  - case 159: `numeric-format` input '1200' in `invoice_line_data.sales_item_account_id` (changed)
  - quickbooks__general_ledger: row 50, unique_id: '8f018a4280336d867e9dfdab85ff0d18' -> '8f5c69aec6d38e5f33591c31e29f4582'
  - quickbooks__general_ledger: row 50, transaction_id: '40113' -> '228'
- **Values change.** If `sales_item_account_id` is the number 00, in `quickbooks__general_ledger`, `unique_id` changes from '8f18f7d13a295e62c1de44f39db8ebbf' to '8f5c69aec6d38e5f33591c31e29f4582' (and 380 more cells).
  - case 161: `numeric-format` input '00' in `invoice_line_data.sales_item_account_id` (changed)
  - quickbooks__general_ledger: row 50, unique_id: '8f18f7d13a295e62c1de44f39db8ebbf' -> '8f5c69aec6d38e5f33591c31e29f4582'
  - quickbooks__general_ledger: row 50, transaction_id: '40113' -> '228'

Proof ID `2d4cf1d338caa865` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v0.15.0/out/integration_tests_dbt_project/proof.json`
