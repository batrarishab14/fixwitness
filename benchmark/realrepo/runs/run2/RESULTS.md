# Real-repository study: results

Run: `f642c6d7ef399a9bbbc0cf10c70868bc40f83e4f study 2026-11-24T17:04:48Z only=`. Protocol: [PROTOCOL.md](PROTOCOL.md). Candidates: [candidates.csv](candidates.csv), frozen before any run. One run per candidate, defaults only (`fixwitness check --base <parent> --no-attacks --warehouse postgres://...`).

## Real bug fixes (would fixwitness have caught the bug?)

| Outcome | Count |
|---|---|
| FAIL | 20 |
| PASS | 30 |
| not checked | 21 |
| **checked** | **50** of 71 |

**Caught: 20/50 (40%) of the checked bug fixes** (FAIL: some valid generated input gives a different output before and after the fix).

| Label | Caught | Missed | Not checked |
|---|---|---|---|
| wrong-data | 19 | 24 | 15 |
| crash-on-data | 1 | 6 | 6 |

## Real refactors (does fixwitness raise false alarms?)

| Outcome | Count |
|---|---|
| PASS | 19 |
| FAIL | 2 |
| not checked | 18 |
| **checked** | **21** of 39 |

**False alarms: 0/21 (0%) of the checked refactors.** Of 2 FAILs, 2 are real differences, 0 false alarms.

| Refactor | Reading | What differs |
|---|---|---|
| `fivetran_log@v2.4.0-a1` | real | On the package's own seed data, fivetran_platform__audit_table has 12 rows instead of 16 and write_to_table_end values change. The release was described as a speed-up (Under the Hood); the notes of the final v2.4.0, for the same PR #174, add a bug fix: duplicate records in fivetran_platform__audit_t |
| `netsuite@v1.7.0` | real | source_relation changes from '<database>.<netsuite_schema>' to '<database>.netsuite2': the migrated macro (fivetran_utils.apply_source_relation, package_name='netsuite2') reads the variable netsuite2_schema, which the project does not set, instead of netsuite_schema, which it does. A project that se |

## Not checked, and why

| Candidate | Set | Why |
|---|---|---|
| `apple_store@v0.3.2` | bug | no valid input could be compared (the original failed on all of them) |
| `apple_store_source@v0.2.1` | bug | - / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / To specify a profile for this project, add a line like the this to |
| `fivetran_log@v2.2.2` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_fivetran_log/.buildkite/scripts; pass one with --sample |
| `google_ads@v1.3.1` | bug | no valid input could be compared (the original failed on all of them) |
| `google_play_source@v0.1.1` | bug | no valid input could be compared (the original failed on all of them) / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / T |
| `google_play_source@v0.3.1` | bug | no valid input could be compared (the original failed on all of them) / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / T |
| `iterable@v1.6.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `iterable_source@v0.10.2` | refactor | no dbt model's compiled SQL changed between the two versions / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_iterable_source/.buildkite/scripts; pass one with --sample |
| `iterable_source@v0.4.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `klaviyo@v0.4.2` | refactor | the sources read the seeds from schema klaviyo, which no variable sets (in integration_tests/dbt_project.yml or as a package default), so they can't be pointed at a private schema in your warehouse |
| `marketo@v1.0.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `marketo@v1.4.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `marketo@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `mixpanel@v0.17.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pardot@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pendo@v0.2.1` | bug | the sources read the seeds from schema pendo, which no variable sets (in integration_tests/dbt_project.yml or as a package default), so they can't be pointed at a private schema in your warehouse |
| `quickbooks@v0.12.3` | bug | no dbt model's compiled SQL changed between the two versions |
| `quickbooks@v0.19.0` | bug | no valid input could be compared (the original failed on all of them) |
| `salesforce@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `shopify@v0.16.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `shopify_source@v0.17.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `shopify_source@v0.18.1` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_shopify_source/.buildkite/scripts; pass one with --sample |
| `stripe_source@v0.9.3` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_stripe_source/.buildkite/scripts; pass one with --sample |
| `workday@v0.1.1` | bug | no valid input could be compared (the original failed on all of them) |
| `workday@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v0.11.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v0.22.0-a1` | bug | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_zendesk/.buildkite/scripts; pass one with --sample |
| `zendesk@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v1.7.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `zendesk@v1.9.0-a3` | bug | no valid input could be compared (the original failed on all of them) |
| `zendesk_source@v0.15.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.17.0-a1` | refactor | no dbt model's compiled SQL changed between the two versions / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_zendesk_source/.buildkite/scripts; pass one with --sample |
| `zendesk_source@v0.18.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.18.2` | bug | no dbt model's compiled SQL changed between the two versions |
| `zuora@v0.2.1` | bug | no valid input could be compared (the original failed on all of them) |
| `zuora@v0.3.2` | bug | no valid input could be compared (the original failed on all of them) / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_zuora/.buildkite/scripts; pass one with --sample |
| `zuora@v0.4.0` | bug | no valid input could be compared (the original failed on all of them) |
| `zuora@v1.4.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `zuora_source@v0.1.2` | bug | no valid input could be compared (the original failed on all of them) |

## Every candidate

| Candidate | Set | Label | Outcome | Differences | Categories | Seconds |
|---|---|---|---|---|---|---|
| `apple_store@v0.3.2` | bug | wrong-data | not checked | 0 |  | 95 |
| `apple_store_source@v0.2.1` | bug | wrong-data | not checked | 0 |  | 33 |
| `fivetran_log@v0.5.4` | bug | wrong-data | PASS | 0 |  | 125 |
| `fivetran_log@v0.6.4` | bug | wrong-data | PASS | 0 |  | 79 |
| `fivetran_log@v0.7.1` | bug | wrong-data | PASS | 0 |  | 102 |
| `fivetran_log@v0.7.2` | bug | wrong-data | PASS | 0 |  | 103 |
| `fivetran_log@v1.2.0` | bug | wrong-data | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 132 |
| `fivetran_log@v1.4.1` | bug | crash-on-data | FAIL | 15 | csv-structure delimiter-mix long punctuation quotes shell-metachar unicode | 68 |
| `github@v0.5.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure flip long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 141 |
| `google_ads@v0.9.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 123 |
| `google_ads@v1.3.1` | bug | wrong-data | not checked | 0 |  | 133 |
| `google_ads_source@v0.9.3` | bug | wrong-data | PASS | 0 |  | 103 |
| `google_play_source@v0.1.1` | bug | wrong-data | not checked | 0 |  | 93 |
| `google_play_source@v0.3.1` | bug | wrong-data | not checked | 0 |  | 91 |
| `hubspot@v1.9.3` | bug | crash-on-data | PASS | 0 |  | 185 |
| `intercom@v0.9.1` | bug | wrong-data | PASS | 0 |  | 84 |
| `jira@v0.12.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 698 |
| `jira@v0.16.0` | bug | crash-on-data | PASS | 0 |  | 493 |
| `jira@v0.8.2` | bug | wrong-data | PASS | 0 |  | 465 |
| `jira@v1.3.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 253 |
| `klaviyo@v1.1.1` | bug | wrong-data | PASS | 0 |  | 84 |
| `klaviyo_source@v0.7.1` | bug | crash-on-data | PASS | 0 |  | 82 |
| `linkedin@v0.6.1` | bug | wrong-data | PASS | 0 |  | 102 |
| `linkedin_source@v0.8.2` | bug | wrong-data | PASS | 0 |  | 76 |
| `marketo@v0.9.1` | bug | wrong-data | PASS | 0 |  | 662 |
| `marketo_source@v0.7.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 119 |
| `netsuite@v0.6.3` | bug | wrong-data | PASS | 0 |  | 142 |
| `pendo@v0.2.1` | bug | crash-on-data | not checked | 0 |  | 27 |
| `quickbooks@v0.12.1` | bug | wrong-data | FAIL | 50 | date-format duplicate empty file-structure null-column numeric-format whitespace | 312 |
| `quickbooks@v0.12.2` | bug | wrong-data | PASS | 0 |  | 141 |
| `quickbooks@v0.12.3` | bug | crash-on-data | not checked | 0 |  | 80 |
| `quickbooks@v0.13.1` | bug | wrong-data | FAIL | 50 | case delimiter-mix duplicate empty file-structure null-column numeric-format whitespace | 275 |
| `quickbooks@v0.14.1` | bug | crash-on-data | PASS | 0 |  | 197 |
| `quickbooks@v0.15.0` | bug | wrong-data | FAIL | 1 | numeric-format | 217 |
| `quickbooks@v0.17.1` | bug | wrong-data | FAIL | 50 | case csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 208 |
| `quickbooks@v0.18.1` | bug | wrong-data | FAIL | 3 | case whitespace | 172 |
| `quickbooks@v0.19.0` | bug | wrong-data | not checked | 0 |  | 154 |
| `quickbooks@v0.5.2` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 181 |
| `quickbooks@v0.5.3` | bug | wrong-data | PASS | 0 |  | 127 |
| `quickbooks@v0.8.1` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 237 |
| `quickbooks@v0.9.1` | bug | wrong-data | PASS | 0 |  | 198 |
| `quickbooks@v1.1.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 173 |
| `quickbooks@v1.2.1` | bug | wrong-data | PASS | 0 |  | 253 |
| `quickbooks@v1.6.2` | bug | wrong-data | PASS | 0 |  | 224 |
| `quickbooks@v1.9.2` | bug | wrong-data | PASS | 0 |  | 258 |
| `sage_intacct@v0.5.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 154 |
| `salesforce@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 63 |
| `salesforce@v1.0.2` | bug | crash-on-data | PASS | 0 |  | 142 |
| `salesforce@v1.1.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 186 |
| `shopify@v0.13.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 311 |
| `shopify@v0.16.1` | bug | wrong-data | not checked | 0 |  | 56 |
| `shopify_source@v0.8.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format schema whitespace | 140 |
| `shopify_source@v0.8.3` | bug | wrong-data | FAIL | 50 | delimiter-mix file-structure schema | 91 |
| `stripe@v0.14.1` | bug | crash-on-data | PASS | 0 |  | 152 |
| `workday@v0.1.1` | bug | wrong-data | not checked | 0 |  | 93 |
| `workday@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 57 |
| `xero@v0.6.2` | bug | wrong-data | PASS | 0 |  | 162 |
| `zendesk@v0.13.1` | bug | wrong-data | PASS | 0 |  | 193 |
| `zendesk@v0.14.0` | bug | wrong-data | PASS | 0 |  | 139 |
| `zendesk@v0.22.0-a1` | bug | wrong-data | not checked | 0 |  | 120 |
| `zendesk@v0.25.0-a1` | bug | wrong-data | PASS | 0 |  | 139 |
| `zendesk@v0.8.1` | bug | wrong-data | PASS | 0 |  | 137 |
| `zendesk@v1.0.1` | bug | wrong-data | not checked | 0 |  | 65 |
| `zendesk@v1.5.1` | bug | wrong-data | PASS | 0 |  | 143 |
| `zendesk@v1.9.0-a3` | bug | wrong-data | not checked | 0 |  | 154 |
| `zendesk_source@v0.18.1` | bug | crash-on-data | not checked | 0 |  | 35 |
| `zendesk_source@v0.18.2` | bug | crash-on-data | not checked | 0 |  | 55 |
| `zuora@v0.2.1` | bug | wrong-data | not checked | 0 |  | 146 |
| `zuora@v0.3.2` | bug | wrong-data | not checked | 0 |  | 151 |
| `zuora@v0.4.0` | bug | wrong-data | not checked | 0 |  | 102 |
| `zuora_source@v0.1.2` | bug | wrong-data | not checked | 0 |  | 131 |
| `asana@v1.4.0` | refactor | refactor | PASS | 0 |  | 136 |
| `fivetran_log@v1.0.1` | refactor | refactor | PASS | 0 |  | 141 |
| `fivetran_log@v2.2.2` | refactor | refactor | not checked | 0 |  | 85 |
| `fivetran_log@v2.4.0-a1` | refactor | refactor | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long pairs punctuation quotes schema shell-metachar unicode | 78 |
| `fivetran_log@v2.5.2` | refactor | refactor | PASS | 0 |  | 100 |
| `github@v1.4.0` | refactor | refactor | PASS | 0 |  | 186 |
| `greenhouse@v1.4.0` | refactor | refactor | PASS | 0 |  | 164 |
| `hubspot@v0.5.2` | refactor | refactor | PASS | 0 |  | 173 |
| `hubspot@v1.8.0` | refactor | refactor | PASS | 0 |  | 196 |
| `intercom@v1.1.0` | refactor | refactor | PASS | 0 |  | 132 |
| `iterable@v1.5.0` | refactor | refactor | PASS | 0 |  | 84 |
| `iterable@v1.6.2` | refactor | refactor | not checked | 0 |  | 36 |
| `iterable_source@v0.10.2` | refactor | refactor | not checked | 0 |  | 47 |
| `iterable_source@v0.4.1` | refactor | refactor | not checked | 0 |  | 26 |
| `jira@v1.10.0` | refactor | refactor | PASS | 0 |  | 124 |
| `klaviyo@v0.4.2` | refactor | refactor | not checked | 0 |  | 10 |
| `mailchimp@v1.3.0` | refactor | refactor | PASS | 0 |  | 79 |
| `marketo@v1.0.1` | refactor | refactor | not checked | 0 |  | 59 |
| `marketo@v1.4.0` | refactor | refactor | not checked | 0 |  | 148 |
| `marketo@v1.4.2` | refactor | refactor | not checked | 0 |  | 63 |
| `mixpanel@v0.17.0` | refactor | refactor | PASS | 0 |  | 89 |
| `mixpanel@v0.17.2` | refactor | refactor | not checked | 0 |  | 27 |
| `netsuite@v1.7.0` | refactor | refactor | FAIL | 50 | duplicate empty numeric-format pairs whitespace | 314 |
| `pardot@v1.4.0` | refactor | refactor | PASS | 0 |  | 78 |
| `pardot@v1.4.2` | refactor | refactor | not checked | 0 |  | 35 |
| `quickbooks@v1.8.1` | refactor | refactor | PASS | 0 |  | 214 |
| `sage_intacct@v1.4.0` | refactor | refactor | PASS | 0 |  | 83 |
| `shopify_source@v0.17.0` | refactor | refactor | not checked | 0 |  | 39 |
| `shopify_source@v0.18.1` | refactor | refactor | not checked | 0 |  | 92 |
| `stripe_source@v0.7.4` | refactor | refactor | PASS | 0 |  | 105 |
| `stripe_source@v0.9.3` | refactor | refactor | not checked | 0 |  | 131 |
| `twilio@v1.4.0` | refactor | refactor | PASS | 0 |  | 67 |
| `zendesk@v0.11.1` | refactor | refactor | not checked | 0 |  | 61 |
| `zendesk@v0.21.0` | refactor | refactor | PASS | 0 |  | 105 |
| `zendesk@v1.7.0` | refactor | refactor | not checked | 0 |  | 116 |
| `zendesk_source@v0.10.0` | refactor | refactor | PASS | 0 |  | 77 |
| `zendesk_source@v0.15.0` | refactor | refactor | not checked | 0 |  | 51 |
| `zendesk_source@v0.17.0-a1` | refactor | refactor | not checked | 0 |  | 54 |
| `zuora@v1.4.0` | refactor | refactor | not checked | 0 |  | 164 |

