# Real-repository study: results

Run: `668553b5240beb5e00f9b4731aca0ab90b148a2d study 2026-11-24T16:22:30Z (run 1); completion of shard 5 at fad15b6 (same code); full logs and proofs: branches study-run1 and study-run1-completion`. Protocol: [PROTOCOL.md](PROTOCOL.md). Candidates: [candidates.csv](candidates.csv), frozen before any run. One run per candidate, defaults only (`fixwitness check --base <parent> --no-attacks --warehouse postgres://...`).

## Real bug fixes (would fixwitness have caught the bug?)

| Outcome | Count |
|---|---|
| FAIL | 22 |
| PASS | 26 |
| not checked | 25 |
| **checked** | **48** of 73 |

**Caught: 22/48 (46%) of the checked bug fixes** (FAIL: some valid generated input gives a different output before and after the fix).

| Label | Caught | Missed | Not checked |
|---|---|---|---|
| wrong-data | 20 | 23 | 17 |
| crash-on-data | 2 | 3 | 8 |

## Real refactors (does fixwitness raise false alarms?)

| Outcome | Count |
|---|---|
| PASS | 18 |
| FAIL | 4 |
| not checked | 21 |
| **checked** | **22** of 43 |

**False alarms: 2/22 (9%) of the checked refactors.** Of 4 FAILs, 2 are real differences, 2 false alarms.

| Refactor | Reading | What differs |
|---|---|---|
| `fivetran_log@v2.4.0-a1` | real | On the package's own seed data, fivetran_platform__audit_table has 12 rows instead of 16 and write_to_table_end values change. The release was described as a speed-up (Under the Hood); the notes of the final v2.4.0, for the same PR #174, add a bug fix: duplicate records in fivetran_platform__audit_t |
| `hubspot@v0.5.2` | false-alarm | The engagement models output the same columns in another order (the macro was rewritten). fixwitness compared SQL result columns by position; it now compares them by name (changed after run 1). Run 2 confirms whether the values are the same. |
| `mixpanel@v0.17.0` | false-alarm | mixpanel__event outputs the same columns in another order. fixwitness compared SQL result columns by position; it now compares them by name (changed after run 1). Run 2 confirms whether the values are the same. |
| `netsuite@v1.7.0` | real | source_relation changes from '<database>.<netsuite_schema>' to '<database>.netsuite2': the migrated macro (fivetran_utils.apply_source_relation, package_name='netsuite2') reads the variable netsuite2_schema, which the project does not set, instead of netsuite_schema, which it does. A project that se |

## Not checked, and why

| Candidate | Set | Why |
|---|---|---|
| `apple_store@v0.3.2` | bug | no valid input could be compared (the original failed on all of them) |
| `apple_store_source@v0.2.1` | bug | - / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / To specify a profile for this project, add a line like the this to |
| `fivetran_log@v0.5.4` | bug | the sources read the seeds from schema fivetran_log, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `fivetran_log@v2.1.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `fivetran_log@v2.2.2` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_fivetran_log/.buildkite/scripts; pass one with --sample |
| `google_ads@v1.3.1` | bug | no valid input could be compared (the original failed on all of them) |
| `google_play_source@v0.1.1` | bug | no valid input could be compared (the original failed on all of them) / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / T |
| `google_play_source@v0.3.1` | bug | no valid input could be compared (the original failed on all of them) / `dbt parse` failed in t0: [ERROR]: Encountered an error: / Runtime Error / dbt cannot run because no profile was specified for this dbt project. / T |
| `hubspot@v1.9.3` | bug | OverflowError: date value out of range |
| `iterable@v1.6.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `iterable_source@v0.10.2` | refactor | no dbt model's compiled SQL changed between the two versions / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_iterable_source/.buildkite/scripts; pass one with --sample |
| `iterable_source@v0.4.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `jira@v1.10.3` | refactor | the GitHub runner was shut down while this shard ran, twice (resources ran out); no result |
| `klaviyo@v0.4.2` | refactor | the sources read the seeds from schema klaviyo, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `marketo@v1.0.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `marketo@v1.4.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `marketo@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `mixpanel@v0.17.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pardot@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pendo@v0.2.1` | bug | the sources read the seeds from schema pendo, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `quickbooks@v0.12.3` | bug | no dbt model's compiled SQL changed between the two versions |
| `quickbooks@v0.19.0` | bug | no valid input could be compared (the original failed on all of them) |
| `salesforce@v1.0.1` | bug | the sources read the seeds from schema salesforce_integrations_tests_3, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `salesforce@v1.0.2` | bug | the sources read the seeds from schema salesforce_integrations_tests_3, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `salesforce@v1.1.1` | bug | the sources read the seeds from schema salesforce_integrations_tests_3, which no variable in integration_tests/dbt_project.yml sets, so they can't be pointed at a private schema in your warehouse |
| `shopify@v0.16.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `shopify_source@v0.15.0` | refactor | the GitHub runner was shut down while this shard ran, twice (resources ran out); no result |
| `shopify_source@v0.17.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `shopify_source@v0.18.1` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_shopify_source/.buildkite/scripts; pass one with --sample |
| `stripe_source@v0.9.3` | refactor | - / no sample input (CSV, JSON Lines or Parquet) found near /home/runner/work/_temp/clones/dbt_stripe_source/.buildkite/scripts; pass one with --sample |
| `workday@v0.1.1` | bug | OverflowError: date value out of range |
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
| `apple_store@v0.3.2` | bug | wrong-data | not checked | 0 |  | 110 |
| `apple_store_source@v0.2.1` | bug | wrong-data | not checked | 0 |  | 45 |
| `fivetran_log@v0.5.4` | bug | wrong-data | not checked | 0 |  | 10 |
| `fivetran_log@v0.6.4` | bug | wrong-data | PASS | 0 |  | 68 |
| `fivetran_log@v0.7.1` | bug | wrong-data | PASS | 0 |  | 101 |
| `fivetran_log@v0.7.2` | bug | wrong-data | PASS | 0 |  | 69 |
| `fivetran_log@v1.2.0` | bug | wrong-data | FAIL | 50 | case delimiter-mix empty file-structure punctuation schema unicode whitespace | 130 |
| `fivetran_log@v1.4.1` | bug | crash-on-data | FAIL | 49 | case csv-structure delimiter-mix long punctuation quotes shell-metachar unicode whitespace | 67 |
| `github@v0.5.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate duplicate-row empty file-structure flip null-column numeric-format pairs punctuation schema time-edge unicode whitespace | 187 |
| `google_ads@v0.9.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 144 |
| `google_ads@v1.3.1` | bug | wrong-data | not checked | 0 |  | 112 |
| `google_ads_source@v0.9.3` | bug | wrong-data | PASS | 0 |  | 84 |
| `google_play_source@v0.1.1` | bug | wrong-data | not checked | 0 |  | 69 |
| `google_play_source@v0.3.1` | bug | wrong-data | not checked | 0 |  | 112 |
| `hubspot@v1.9.3` | bug | crash-on-data | not checked | 0 |  | 77 |
| `intercom@v0.9.1` | bug | wrong-data | PASS | 0 |  | 87 |
| `jira@v0.12.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 406 |
| `jira@v0.16.0` | bug | crash-on-data | PASS | 0 |  | 290 |
| `jira@v0.8.2` | bug | wrong-data | PASS | 0 |  | 469 |
| `jira@v1.3.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format pairs schema unicode whitespace | 235 |
| `klaviyo@v1.1.1` | bug | wrong-data | PASS | 0 |  | 73 |
| `klaviyo_source@v0.7.1` | bug | crash-on-data | PASS | 0 |  | 99 |
| `linkedin@v0.6.1` | bug | wrong-data | PASS | 0 |  | 61 |
| `linkedin_source@v0.8.2` | bug | wrong-data | PASS | 0 |  | 66 |
| `marketo@v0.9.1` | bug | wrong-data | PASS | 0 |  | 409 |
| `marketo_source@v0.7.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 116 |
| `netsuite@v0.6.3` | bug | wrong-data | PASS | 0 |  | 139 |
| `pendo@v0.2.1` | bug | crash-on-data | not checked | 0 |  | 27 |
| `quickbooks@v0.12.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 294 |
| `quickbooks@v0.12.2` | bug | wrong-data | PASS | 0 |  | 152 |
| `quickbooks@v0.12.3` | bug | crash-on-data | not checked | 0 |  | 58 |
| `quickbooks@v0.13.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 168 |
| `quickbooks@v0.14.1` | bug | crash-on-data | PASS | 0 |  | 220 |
| `quickbooks@v0.15.0` | bug | wrong-data | FAIL | 11 | numeric-format whitespace | 193 |
| `quickbooks@v0.17.1` | bug | wrong-data | FAIL | 50 | case duplicate empty file-structure null-column pairs time-edge whitespace | 269 |
| `quickbooks@v0.18.1` | bug | wrong-data | FAIL | 3 | case whitespace | 111 |
| `quickbooks@v0.19.0` | bug | wrong-data | not checked | 0 |  | 155 |
| `quickbooks@v0.5.1` | bug | wrong-data | FAIL | 50 | case date-format delimiter-mix duplicate empty file-structure null-column numeric-format unicode whitespace | 194 |
| `quickbooks@v0.5.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 267 |
| `quickbooks@v0.5.3` | bug | wrong-data | PASS | 0 |  | 132 |
| `quickbooks@v0.8.1` | bug | wrong-data | FAIL | 50 | case date-format duplicate empty file-structure null-column numeric-format schema whitespace | 230 |
| `quickbooks@v0.9.1` | bug | wrong-data | PASS | 0 |  | 199 |
| `quickbooks@v1.1.0` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure null-column numeric-format pairs schema whitespace | 148 |
| `quickbooks@v1.2.1` | bug | wrong-data | FAIL | 1 | null-column | 267 |
| `quickbooks@v1.6.2` | bug | wrong-data | PASS | 0 |  | 144 |
| `quickbooks@v1.9.2` | bug | wrong-data | PASS | 0 |  | 243 |
| `sage_intacct@v0.5.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 147 |
| `salesforce@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 12 |
| `salesforce@v1.0.2` | bug | crash-on-data | not checked | 0 |  | 8 |
| `salesforce@v1.1.1` | bug | wrong-data | not checked | 0 |  | 8 |
| `shopify@v0.13.2` | bug | wrong-data | FAIL | 1 | file-structure | 138 |
| `shopify@v0.16.1` | bug | wrong-data | not checked | 0 |  | 53 |
| `shopify_source@v0.8.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format schema whitespace | 140 |
| `shopify_source@v0.8.3` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format pairs schema whitespace | 90 |
| `stripe@v0.14.1` | bug | crash-on-data | FAIL | 1 | numeric-format | 108 |
| `workday@v0.1.1` | bug | wrong-data | not checked | 0 |  | 59 |
| `workday@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 47 |
| `xero@v0.6.2` | bug | wrong-data | PASS | 0 |  | 118 |
| `zendesk@v0.13.1` | bug | wrong-data | PASS | 0 |  | 185 |
| `zendesk@v0.14.0` | bug | wrong-data | PASS | 0 |  | 136 |
| `zendesk@v0.18.1` | bug | wrong-data | PASS | 0 |  | 136 |
| `zendesk@v0.22.0-a1` | bug | wrong-data | not checked | 0 |  | 115 |
| `zendesk@v0.25.0-a1` | bug | wrong-data | PASS | 0 |  | 124 |
| `zendesk@v0.8.1` | bug | wrong-data | PASS | 0 |  | 90 |
| `zendesk@v1.0.1` | bug | wrong-data | not checked | 0 |  | 55 |
| `zendesk@v1.5.1` | bug | wrong-data | PASS | 0 |  | 160 |
| `zendesk@v1.9.0-a3` | bug | wrong-data | not checked | 0 |  | 110 |
| `zendesk_source@v0.18.1` | bug | crash-on-data | not checked | 0 |  | 34 |
| `zendesk_source@v0.18.2` | bug | crash-on-data | not checked | 0 |  | 53 |
| `zuora@v0.2.1` | bug | wrong-data | not checked | 0 |  | 90 |
| `zuora@v0.3.2` | bug | wrong-data | not checked | 0 |  | 140 |
| `zuora@v0.4.0` | bug | wrong-data | not checked | 0 |  | 91 |
| `zuora_source@v0.1.2` | bug | wrong-data | not checked | 0 |  | 103 |
| `asana@v1.4.0` | refactor | refactor | PASS | 0 |  | 139 |
| `fivetran_log@v1.0.1` | refactor | refactor | PASS | 0 |  | 88 |
| `fivetran_log@v2.1.0` | refactor | refactor | not checked | 0 |  | 44 |
| `fivetran_log@v2.2.2` | refactor | refactor | not checked | 0 |  | 143 |
| `fivetran_log@v2.4.0-a1` | refactor | refactor | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 85 |
| `fivetran_log@v2.5.2` | refactor | refactor | PASS | 0 |  | 101 |
| `github@v1.4.0` | refactor | refactor | PASS | 0 |  | 121 |
| `greenhouse@v1.4.0` | refactor | refactor | PASS | 0 |  | 112 |
| `hubspot@v0.5.2` | refactor | refactor | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode whitespace | 201 |
| `hubspot@v1.8.0` | refactor | refactor | PASS | 0 |  | 118 |
| `intercom@v1.1.0` | refactor | refactor | PASS | 0 |  | 144 |
| `iterable@v1.5.0` | refactor | refactor | PASS | 0 |  | 145 |
| `iterable@v1.6.2` | refactor | refactor | not checked | 0 |  | 36 |
| `iterable_source@v0.10.2` | refactor | refactor | not checked | 0 |  | 32 |
| `iterable_source@v0.4.1` | refactor | refactor | not checked | 0 |  | 27 |
| `jira@v1.10.0` | refactor | refactor | PASS | 0 |  | 116 |
| `jira@v1.10.3` | refactor | refactor | not checked |  |  |  |
| `klaviyo@v0.4.2` | refactor | refactor | not checked | 0 |  | 9 |
| `mailchimp@v1.3.0` | refactor | refactor | PASS | 0 |  | 107 |
| `marketo@v1.0.1` | refactor | refactor | not checked | 0 |  | 43 |
| `marketo@v1.4.0` | refactor | refactor | not checked | 0 |  | 165 |
| `marketo@v1.4.2` | refactor | refactor | not checked | 0 |  | 54 |
| `mixpanel@v0.17.0` | refactor | refactor | FAIL | 50 | delimiter-mix | 127 |
| `mixpanel@v0.17.2` | refactor | refactor | not checked | 0 |  | 28 |
| `netsuite@v1.7.0` | refactor | refactor | FAIL | 50 | case whitespace | 362 |
| `pardot@v1.4.0` | refactor | refactor | PASS | 0 |  | 136 |
| `pardot@v1.4.2` | refactor | refactor | not checked | 0 |  | 36 |
| `pendo@v1.4.0` | refactor | refactor | PASS | 0 |  | 96 |
| `quickbooks@v1.8.1` | refactor | refactor | PASS | 0 |  | 128 |
| `sage_intacct@v1.4.0` | refactor | refactor | PASS | 0 |  | 80 |
| `shopify_source@v0.15.0` | refactor | refactor | not checked |  |  |  |
| `shopify_source@v0.17.0` | refactor | refactor | not checked | 0 |  | 72 |
| `shopify_source@v0.18.1` | refactor | refactor | not checked | 0 |  | 84 |
| `stripe_source@v0.7.4` | refactor | refactor | PASS | 0 |  | 67 |
| `stripe_source@v0.9.3` | refactor | refactor | not checked | 0 |  | 80 |
| `twilio@v1.4.0` | refactor | refactor | PASS | 0 |  | 89 |
| `zendesk@v0.11.1` | refactor | refactor | not checked | 0 |  | 40 |
| `zendesk@v0.21.0` | refactor | refactor | PASS | 0 |  | 221 |
| `zendesk@v1.7.0` | refactor | refactor | not checked | 0 |  | 120 |
| `zendesk_source@v0.10.0` | refactor | refactor | PASS | 0 |  | 106 |
| `zendesk_source@v0.15.0` | refactor | refactor | not checked | 0 |  | 36 |
| `zendesk_source@v0.17.0-a1` | refactor | refactor | not checked | 0 |  | 58 |
| `zuora@v1.4.0` | refactor | refactor | not checked | 0 |  | 145 |

