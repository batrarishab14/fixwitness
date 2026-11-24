## fixwitness: INCONCLUSIVE (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | PASS 99/100 | - |
| `.buildkite/scripts/run_models.sh` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_shopify_source/.buildkite/scripts; pass one with --sample |

Not checked: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `LICENSE` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.
