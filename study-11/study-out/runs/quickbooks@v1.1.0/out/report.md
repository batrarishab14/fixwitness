## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `quickbooks__ap_ar_enhanced`, `is_overdue` changes from 'true' to 'false' (and 19 more cells). |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `e7b6059ae479` (original) vs working tree (fix); changed: `.quickstart/quickstart.yml`, `CHANGELOG.md`, `README.md`, `dbt_project.yml`, `docs/catalog.json` and 4 more. dbt project: changed `quickbooks__ap_ar_enhanced`; compared `quickbooks__ap_ar_enhanced`; SQL on warehouse; tables `bill_payment_data` (bill_payment_data.csv), `address_data` (address_data.csv), `estimate_data` (estimate_data.csv), `bill_linked_txn_data` (bill_linked_txn_data.csv), `payment_data` (payment_data.csv), `customer_data` (customer_data.csv), `payment_line_data` (payment_line_data.csv), `department_data` (department_data.csv), `bill_data` (bill_data.csv), `invoice_data` (invoice_data.csv), `invoice_linked_txn_data` (invoice_linked_txn_data.csv), `bill_payment_line_data` (bill_payment_line_data.csv), `vendor_data` (vendor_data.csv), `bill_line_data` (bill_line_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 296 comparable valid inputs give the same output |
| Needs review | 4 of 4 inputs in review categories (inputs that break your dbt tests (stg_quickbooks__bill_linked_txn: not_null(bill_id); stg_quickbooks__payment_line: not_null(payment_id))) differ |

**Why:** the fix changes output on 296 valid inputs.

**What could go wrong:**

- **Values change.** If the file is tables as given, in `quickbooks__ap_ar_enhanced`, `is_overdue` changes from 'true' to 'false' (and 19 more cells).
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If a `bill_payment_data` row has an empty `department_id`, in `quickbooks__ap_ar_enhanced`, `is_overdue` for 'invoice' changes from 'true' to 'false' (and 1 more cell).
  - case 001: `empty` input '' in `bill_payment_data.department_id` (changed); input shrunk to the rows that show it
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If `department_id` repeats the value of another row (''), in `quickbooks__ap_ar_enhanced`, `is_overdue` for 'invoice' changes from 'true' to 'false' (and 1 more cell).
  - case 002: `duplicate` input '' in `bill_payment_data.department_id` (changed); input shrunk to the rows that show it
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If a `bill_payment_data` row has an empty `doc_number`, in `quickbooks__ap_ar_enhanced`, `is_overdue` for 'invoice' changes from 'true' to 'false' (and 1 more cell).
  - case 003: `empty` input '' in `bill_payment_data.doc_number` (changed); input shrunk to the rows that show it
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If `doc_number` repeats the value of another row (''), in `quickbooks__ap_ar_enhanced`, `is_overdue` for 'invoice' changes from 'true' to 'false' (and 1 more cell).
  - case 004: `duplicate` input '' in `bill_payment_data.doc_number` (changed); input shrunk to the rows that show it
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If `exchange_rate` is the number 0, in `quickbooks__ap_ar_enhanced`, `is_overdue` for 'invoice' changes from 'true' to 'false' (and 1 more cell).
  - case 005: `numeric-format` input '0' in `bill_payment_data.exchange_rate` (changed); input shrunk to the rows that show it
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If `exchange_rate` has extra spaces (' 42 '), in `quickbooks__ap_ar_enhanced`, `is_overdue` changes from 'true' to 'false' (and 19 more cells).
  - case 006: `whitespace` input ' 42 ' in `bill_payment_data.exchange_rate` (changed)
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'
- **Values change.** If a `bill_payment_data` row has an empty `exchange_rate`, in `quickbooks__ap_ar_enhanced`, `is_overdue` changes from 'true' to 'false' (and 19 more cells).
  - case 007: `empty` input '' in `bill_payment_data.exchange_rate` (changed)
  - quickbooks__ap_ar_enhanced: row 3, is_overdue: 'true' -> 'false'
  - quickbooks__ap_ar_enhanced: row 3, days_overdue: '2168' -> '0'

Proof ID `f894b37f5af2b8cb` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/quickbooks@v1.1.0/out/integration_tests_dbt_project/proof.json`
