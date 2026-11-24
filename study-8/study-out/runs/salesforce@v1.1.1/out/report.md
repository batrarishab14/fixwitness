## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | not checked | the sources read the seeds from schema salesforce_integrations_tests_3, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)
