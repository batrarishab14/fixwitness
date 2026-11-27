## fixwitness: INCONCLUSIVE (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | PASS 99/100 | - |
| `. (dbt project)` | dbt | not checked | no sample for the dbt source(s) apple_store.sales_subscription_event_summary: put a CSV named after each table in the project's seeds/ or data/ folder, or pass --table sales_subscription_event_summary=FILE |

Not checked: `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.
