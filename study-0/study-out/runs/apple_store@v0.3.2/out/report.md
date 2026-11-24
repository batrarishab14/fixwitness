## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |

Not checked: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `.gitignore` (not code); `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `955784a174ea` (original) vs working tree (fix); changed: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md`, `.github/workflows/auto-release.yml`, `.gitignore`, `CHANGELOG.md`, `dbt_project.yml` and 7 more. dbt project: changed `apple_store__subscription_report`; compared `apple_store__subscription_report`; SQL on warehouse; tables `app` (app.csv), `sales_subscription_summary` (sales_subscription_summary.csv), `sales_account` (sales_account.csv), `sales_subscription_events` (sales_subscription_events.csv), `apple_store_country_codes` (apple_store_country_codes.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 286 valid inputs made the original fail too |
| Needs review | 0 of 14 inputs in review categories (inputs that break your dbt tests (stg_apple_store__app: unique(app_id); stg_apple_store__sales_account: unique(account_id))) differ |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: value ' ' in sales_subscription_events.days_canceled is not an integer
- Note: 286 valid inputs could not be compared because the original failed on them

Proof ID `02e1dfd9c83d89ae` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/apple_store@v0.3.2/out/integration_tests_dbt_project/proof.json`
