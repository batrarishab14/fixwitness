## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | not exercisable with this data: no input reaches what the change touched ('sub%'), so identical output proves nothing about it; add rows that have it |

Not checked: `.buildkite/scripts/run_models.sh` (CI configuration); `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `.github/pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `4be5791d886e` (original) vs working tree (fix); changed: `.buildkite/scripts/run_models.sh`, `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md`, `.github/pull_request_template.md`, `CHANGELOG.md`, `README.md` and 29 more. dbt project: changed `stg_stripe__charge`, `stg_stripe__charge_tmp`, `stg_stripe__credit_note`, `stg_stripe__credit_note_line_item`, `stg_stripe__credit_note_line_item_tmp`, `stg_stripe__credit_note_tmp`, `stg_stripe__customer`, `stg_stripe__customer_tmp`, `stg_stripe__invoice`, `stg_stripe__invoice_line_item`, `stg_stripe__invoice_line_item_tmp`, `stg_stripe__invoice_tmp`, `stg_stripe__payment_intent`, `stg_stripe__payment_intent_tmp`, `stg_stripe__payment_method`, `stg_stripe__payment_method_tmp`, `stg_stripe__payout`, `stg_stripe__payout_tmp`, `stg_stripe__price_plan`, `stg_stripe__price_plan_tmp`, `stg_stripe__subscription`, `stg_stripe__subscription_tmp`; compared `stg_stripe__charge`, `stg_stripe__credit_note`, `stg_stripe__credit_note_line_item`, `stg_stripe__customer`, `stg_stripe__invoice`, `stg_stripe__invoice_line_item`, `stg_stripe__payment_intent`, `stg_stripe__payment_method`, `stg_stripe__payout`, `stg_stripe__price_plan`, `stg_stripe__subscription`; SQL on warehouse; tables `price_data` (price_data.csv), `customer_data` (customer_data.csv), `payment_intent_data` (payment_intent_data.csv), `payout_data` (payout_data.csv), `payment_method_data` (payment_method_data.csv), `invoice_data` (invoice_data.csv), `credit_note_data` (credit_note_data.csv), `charge_data` (charge_data.csv), `subscription_history_data` (subscription_history_data.csv), `invoice_line_item_data` (invoice_line_item_data.csv), `credit_note_line_item_data` (credit_note_line_item_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | PASS: 300 of 300 comparable valid inputs give the same output |

**Why:** not exercisable with this data: no input reaches what the change touched ('sub%'), so identical output proves nothing about it; add rows that have it.

Proof ID `1cb363e4b65863db` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/stripe_source@v0.9.3/out/integration_tests_dbt_project/proof.json`
