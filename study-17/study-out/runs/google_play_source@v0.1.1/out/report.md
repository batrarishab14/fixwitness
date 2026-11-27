## fixwitness: INCONCLUSIVE (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | PASS 99/100 | - |
| `. (dbt project)` | dbt | not checked | no sample for the dbt source(s) google_play.stats_ratings_app_version, google_play.stats_ratings_country, google_play.stats_ratings_device, google_play.stats_ratings_os_version, google_play.stats_ratings_overview: put a CSV named after each table in the project's seeds/ or data/ folder, or pass --ta |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.
