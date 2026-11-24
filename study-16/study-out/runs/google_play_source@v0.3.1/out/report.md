## fixwitness: INCONCLUSIVE (3 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |
| `. (dbt project)` | dbt | not checked | `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / To specify a profile for this project, add a line like the this to |
| `.buildkite/hooks/pre-command` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_google_play_source/.buildkite/hooks; pass one with --sample |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `7c0b3c31fd7f` (original) vs working tree (fix); changed: `.buildkite/hooks/pre-command`, `.buildkite/pipeline.yml`, `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json` and 21 more. dbt project: changed `stg_google_play__stats_crashes_app_version`, `stg_google_play__stats_crashes_os_version`, `stg_google_play__stats_crashes_overview`, `stg_google_play__stats_installs_app_version`, `stg_google_play__stats_installs_country`, `stg_google_play__stats_installs_device`, `stg_google_play__stats_installs_os_version`, `stg_google_play__stats_installs_overview`, `stg_google_play__stats_ratings_app_version`, `stg_google_play__stats_ratings_country`, `stg_google_play__stats_ratings_device`, `stg_google_play__stats_ratings_os_version`, `stg_google_play__stats_ratings_overview`, `stg_google_play__store_performance_country`, `stg_google_play__store_performance_source`; compared `stg_google_play__stats_crashes_app_version`, `stg_google_play__stats_crashes_os_version`, `stg_google_play__stats_crashes_overview`, `stg_google_play__stats_installs_app_version`, `stg_google_play__stats_installs_country`, `stg_google_play__stats_installs_device`, `stg_google_play__stats_installs_os_version`, `stg_google_play__stats_installs_overview`, `stg_google_play__stats_ratings_app_version`, `stg_google_play__stats_ratings_country`, `stg_google_play__stats_ratings_device`, `stg_google_play__stats_ratings_os_version`, `stg_google_play__stats_ratings_overview`, `stg_google_play__store_performance_country`, `stg_google_play__store_performance_source`; SQL on warehouse; tables `stats_store_performance_country` (stats_store_performance_country.csv), `stats_installs_app_version` (stats_installs_app_version.csv), `stats_crashes_overview` (stats_crashes_overview.csv), `stats_crashes_os_version` (stats_crashes_os_version.csv), `stats_installs_country` (stats_installs_country.csv), `stats_ratings_overview` (stats_ratings_overview.csv), `stats_installs_overview` (stats_installs_overview.csv), `stats_installs_os_version` (stats_installs_os_version.csv), `stats_store_performance_traffic_source` (stats_store_performance_traffic_source.csv), `stats_ratings_country` (stats_ratings_country.csv), `stats_ratings_device` (stats_ratings_device.csv), `stats_crashes_app_version` (stats_crashes_app_version.csv), `stats_ratings_os_version` (stats_ratings_os_version.csv), `stats_installs_device` (stats_installs_device.csv), `stats_ratings_app_version` (stats_ratings_app_version.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 294 valid inputs made the original fail too |
| Needs review | 0 of 6 inputs in review categories (inputs that break your dbt tests (stg_google_play__stats_crashes_overview: unique_combination_of_columns(package_name, date_day); stg_google_play__stats_installs_overview: unique_combination_of_columns(package_name, date_day); stg_google_play__stats_ratings_overview: unique_combination_of_columns(package_name, date_day))) differ |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: table stats_ratings_overview has an empty or repeated column name
- Note: 294 valid inputs could not be compared because the original failed on them

Proof ID `a22b83cff57ea949` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/google_play_source@v0.3.1/out/integration_tests_dbt_project/proof.json`
