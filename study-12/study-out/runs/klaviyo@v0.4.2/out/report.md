## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | not checked | the sources read the seeds from schema klaviyo, which no variable sets (in integration_tests/dbt_project.yml or as a package default), so they can't be pointed at a private schema in your warehouse |

Not checked: `.github/pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `README.md` (documentation); `docs/catalog.json` (not code); `docs/graph.gpickle` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/partial_parse.msgpack` (not code); `docs/run_results.json` (not code); `integration_tests/requirements.txt` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.
