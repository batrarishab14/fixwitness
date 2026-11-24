## fixwitness: INCONCLUSIVE (2 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | not checked | no dbt model's compiled SQL changed between the two versions |
| `.buildkite/scripts/run_models.sh` | script | not checked | no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_iterable_source/.buildkite/scripts; pass one with --sample |

Not checked: `.gitignore` (not code); `CHANGELOG.md` (documentation); `integration_tests/requirements.txt` (not code)

To see what is missing and the command that fixes it: `fixwitness doctor`.
