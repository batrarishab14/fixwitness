# Real-repository study: results

Run: `7265067106508bd17cb86650c5922259592f7b92 study 2026-11-24T18:16:44Z only=`. Protocol: [PROTOCOL.md](PROTOCOL.md). Candidates: [candidates.csv](candidates.csv), frozen before any run. One run per candidate, defaults only (`fixwitness check --base <parent> --no-attacks --warehouse postgres://...`).

## Real bug fixes (would fixwitness have caught the bug?)

| Outcome | Count |
|---|---|
| FAIL | 27 |
| PASS | 30 |
| not checked | 14 |
| **checked** | **57** of 71 |

**Caught: 27/57 (47%) of the checked bug fixes** (FAIL: some valid generated input gives a different output before and after the fix).

| Label | Caught | Missed | Not checked |
|---|---|---|---|
| wrong-data | 25 | 25 | 8 |
| crash-on-data | 2 | 5 | 6 |

## Real refactors (does fixwitness raise false alarms?)

| Outcome | Count |
|---|---|
| PASS | 23 |
| FAIL | 2 |
| not checked | 14 |
| **checked** | **25** of 39 |

**False alarms: 0/25 (0%) of the checked refactors.** Of 2 FAILs, 0 are real differences, 0 false alarms, 2 not yet read.

| Refactor | Reading | What differs |
|---|---|---|
| `fivetran_log@v2.4.0-a1` | not yet read | If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing. |
| `netsuite@v1.7.0` | not yet read | If `id` is the number 0, in `netsuite2__entity_subsidiary_relationships`, the output has 1 row instead of 1; a new row for 'test.netsuite2' appears. |

## Not checked, and why

| Candidate | Set | Why |
|---|---|---|
| `apple_store_source@v0.2.1` | bug | - / no dbt model's compiled SQL changed between the two versions |
| `google_play_source@v0.1.1` | bug | no valid input could be compared (the original failed on all of them) / no sample for the dbt source(s) google_play.stats_ratings_app_version, google_play.stats_ratings_country, google_play.stats_ratings_device, google_p |
| `google_play_source@v0.3.1` | bug | no valid input could be compared (the original failed on all of them) / no sample for the dbt source(s) google_play.stats_crashes_app_version, google_play.stats_crashes_os_version, google_play.stats_crashes_overview, goo |
| `iterable@v1.6.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `iterable_source@v0.10.2` | refactor | no dbt model's compiled SQL changed between the two versions |
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
| `workday@v0.1.1` | bug | no valid input could be compared (the original failed on all of them) |
| `workday@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v0.11.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v1.7.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `zendesk@v1.9.0-a3` | bug | no valid input could be compared (the original failed on all of them) |
| `zendesk_source@v0.15.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.17.0-a1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.18.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.18.2` | bug | no dbt model's compiled SQL changed between the two versions |

## Every candidate

| Candidate | Set | Label | Outcome | Differences | Categories | Seconds |
|---|---|---|---|---|---|---|
| `apple_store@v0.3.2` | bug | wrong-data | FAIL | 50 | delimiter-mix empty unicode whitespace | 153 |
| `apple_store_source@v0.2.1` | bug | wrong-data | not checked | 0 |  | 89 |
| `fivetran_log@v0.5.4` | bug | wrong-data | PASS | 0 |  | 121 |
| `fivetran_log@v0.6.4` | bug | wrong-data | PASS | 0 |  | 69 |
| `fivetran_log@v0.7.1` | bug | wrong-data | PASS | 0 |  | 105 |
| `fivetran_log@v0.7.2` | bug | wrong-data | PASS | 0 |  | 101 |
| `fivetran_log@v1.2.0` | bug | wrong-data | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 142 |
| `fivetran_log@v1.4.1` | bug | crash-on-data | FAIL | 7 | csv-structure delimiter-mix long punctuation quotes shell-metachar unicode | 103 |
| `github@v0.5.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure flip long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 150 |
| `google_ads@v0.9.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate-row empty file-structure flip long null-column numeric-format pairs punctuation quotes schema shell-metachar time-edge unicode whitespace | 104 |
| `google_ads@v1.3.1` | bug | wrong-data | PASS | 0 |  | 126 |
| `google_ads_source@v0.9.3` | bug | wrong-data | PASS | 0 |  | 88 |
| `google_play_source@v0.1.1` | bug | wrong-data | not checked | 0 |  | 146 |
| `google_play_source@v0.3.1` | bug | wrong-data | not checked | 0 |  | 110 |
| `hubspot@v1.9.3` | bug | crash-on-data | PASS | 0 |  | 153 |
| `intercom@v0.9.1` | bug | wrong-data | PASS | 0 |  | 107 |
| `jira@v0.12.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 629 |
| `jira@v0.16.0` | bug | crash-on-data | PASS | 0 |  | 434 |
| `jira@v0.8.2` | bug | wrong-data | PASS | 0 |  | 467 |
| `jira@v1.3.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 277 |
| `klaviyo@v1.1.1` | bug | wrong-data | PASS | 0 |  | 71 |
| `klaviyo_source@v0.7.1` | bug | crash-on-data | PASS | 0 |  | 94 |
| `linkedin@v0.6.1` | bug | wrong-data | PASS | 0 |  | 96 |
| `linkedin_source@v0.8.2` | bug | wrong-data | PASS | 0 |  | 64 |
| `marketo@v0.9.1` | bug | wrong-data | PASS | 0 |  | 537 |
| `marketo_source@v0.7.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 167 |
| `netsuite@v0.6.3` | bug | wrong-data | PASS | 0 |  | 179 |
| `pendo@v0.2.1` | bug | crash-on-data | not checked | 0 |  | 36 |
| `quickbooks@v0.12.1` | bug | wrong-data | FAIL | 50 | date-format duplicate empty file-structure null-column numeric-format whitespace | 320 |
| `quickbooks@v0.12.2` | bug | wrong-data | PASS | 0 |  | 214 |
| `quickbooks@v0.12.3` | bug | crash-on-data | not checked | 0 |  | 63 |
| `quickbooks@v0.13.1` | bug | wrong-data | FAIL | 50 | case csv-structure date-format delimiter-mix duplicate duplicate-row empty file-structure flip long null-column numeric-format pairs punctuation quotes schema shell-metachar time-edge unicode whitespace | 299 |
| `quickbooks@v0.14.1` | bug | crash-on-data | PASS | 0 |  | 183 |
| `quickbooks@v0.15.0` | bug | wrong-data | FAIL | 2 | numeric-format whitespace | 205 |
| `quickbooks@v0.17.1` | bug | wrong-data | FAIL | 50 | case csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 225 |
| `quickbooks@v0.18.1` | bug | wrong-data | FAIL | 18 | case csv-structure date-format delimiter-mix flip long punctuation quotes shell-metachar unicode | 169 |
| `quickbooks@v0.19.0` | bug | wrong-data | not checked | 0 |  | 152 |
| `quickbooks@v0.5.2` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 201 |
| `quickbooks@v0.5.3` | bug | wrong-data | PASS | 0 |  | 137 |
| `quickbooks@v0.8.1` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 283 |
| `quickbooks@v0.9.1` | bug | wrong-data | PASS | 0 |  | 173 |
| `quickbooks@v1.1.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 151 |
| `quickbooks@v1.2.1` | bug | wrong-data | FAIL | 1 | null-column | 292 |
| `quickbooks@v1.6.2` | bug | wrong-data | PASS | 0 |  | 217 |
| `quickbooks@v1.9.2` | bug | wrong-data | PASS | 0 |  | 288 |
| `sage_intacct@v0.5.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode | 166 |
| `salesforce@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 59 |
| `salesforce@v1.0.2` | bug | crash-on-data | PASS | 0 |  | 137 |
| `salesforce@v1.1.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode | 170 |
| `shopify@v0.13.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 288 |
| `shopify@v0.16.1` | bug | wrong-data | not checked | 0 |  | 48 |
| `shopify_source@v0.8.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format schema whitespace | 156 |
| `shopify_source@v0.8.3` | bug | wrong-data | FAIL | 50 | delimiter-mix file-structure schema | 123 |
| `stripe@v0.14.1` | bug | crash-on-data | FAIL | 1 | numeric-format | 149 |
| `workday@v0.1.1` | bug | wrong-data | not checked | 0 |  | 91 |
| `workday@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 50 |
| `xero@v0.6.2` | bug | wrong-data | PASS | 0 |  | 198 |
| `zendesk@v0.13.1` | bug | wrong-data | PASS | 0 |  | 210 |
| `zendesk@v0.14.0` | bug | wrong-data | PASS | 0 |  | 199 |
| `zendesk@v0.22.0-a1` | bug | wrong-data | PASS | 0 |  | 130 |
| `zendesk@v0.25.0-a1` | bug | wrong-data | PASS | 0 |  | 148 |
| `zendesk@v0.8.1` | bug | wrong-data | PASS | 0 |  | 136 |
| `zendesk@v1.0.1` | bug | wrong-data | not checked | 0 |  | 56 |
| `zendesk@v1.5.1` | bug | wrong-data | PASS | 0 |  | 156 |
| `zendesk@v1.9.0-a3` | bug | wrong-data | not checked | 0 |  | 138 |
| `zendesk_source@v0.18.1` | bug | crash-on-data | not checked | 0 |  | 31 |
| `zendesk_source@v0.18.2` | bug | crash-on-data | not checked | 0 |  | 52 |
| `zuora@v0.2.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 232 |
| `zuora@v0.3.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 263 |
| `zuora@v0.4.0` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long pairs punctuation quotes shell-metachar unicode whitespace | 154 |
| `zuora_source@v0.1.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 184 |
| `asana@v1.4.0` | refactor | refactor | PASS | 0 |  | 123 |
| `fivetran_log@v1.0.1` | refactor | refactor | PASS | 0 |  | 126 |
| `fivetran_log@v2.2.2` | refactor | refactor | PASS | 0 |  | 92 |
| `fivetran_log@v2.4.0-a1` | refactor | refactor | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 88 |
| `fivetran_log@v2.5.2` | refactor | refactor | PASS | 0 |  | 126 |
| `github@v1.4.0` | refactor | refactor | PASS | 0 |  | 216 |
| `greenhouse@v1.4.0` | refactor | refactor | PASS | 0 |  | 188 |
| `hubspot@v0.5.2` | refactor | refactor | PASS | 0 |  | 166 |
| `hubspot@v1.8.0` | refactor | refactor | PASS | 0 |  | 296 |
| `intercom@v1.1.0` | refactor | refactor | PASS | 0 |  | 115 |
| `iterable@v1.5.0` | refactor | refactor | PASS | 0 |  | 95 |
| `iterable@v1.6.2` | refactor | refactor | not checked | 0 |  | 36 |
| `iterable_source@v0.10.2` | refactor | refactor | not checked | 0 |  | 36 |
| `iterable_source@v0.4.1` | refactor | refactor | not checked | 0 |  | 42 |
| `jira@v1.10.0` | refactor | refactor | PASS | 0 |  | 173 |
| `klaviyo@v0.4.2` | refactor | refactor | not checked | 0 |  | 10 |
| `mailchimp@v1.3.0` | refactor | refactor | PASS | 0 |  | 90 |
| `marketo@v1.0.1` | refactor | refactor | not checked | 0 |  | 71 |
| `marketo@v1.4.0` | refactor | refactor | not checked | 0 |  | 119 |
| `marketo@v1.4.2` | refactor | refactor | not checked | 0 |  | 55 |
| `mixpanel@v0.17.0` | refactor | refactor | PASS | 0 |  | 102 |
| `mixpanel@v0.17.2` | refactor | refactor | not checked | 0 |  | 46 |
| `netsuite@v1.7.0` | refactor | refactor | FAIL | 50 | duplicate empty numeric-format pairs whitespace | 280 |
| `pardot@v1.4.0` | refactor | refactor | PASS | 0 |  | 85 |
| `pardot@v1.4.2` | refactor | refactor | not checked | 0 |  | 34 |
| `quickbooks@v1.8.1` | refactor | refactor | PASS | 0 |  | 188 |
| `sage_intacct@v1.4.0` | refactor | refactor | PASS | 0 |  | 118 |
| `shopify_source@v0.17.0` | refactor | refactor | not checked | 0 |  | 42 |
| `shopify_source@v0.18.1` | refactor | refactor | PASS | 0 |  | 85 |
| `stripe_source@v0.7.4` | refactor | refactor | PASS | 0 |  | 105 |
| `stripe_source@v0.9.3` | refactor | refactor | PASS | 0 |  | 118 |
| `twilio@v1.4.0` | refactor | refactor | PASS | 0 |  | 73 |
| `zendesk@v0.11.1` | refactor | refactor | not checked | 0 |  | 56 |
| `zendesk@v0.21.0` | refactor | refactor | PASS | 0 |  | 114 |
| `zendesk@v1.7.0` | refactor | refactor | not checked | 0 |  | 174 |
| `zendesk_source@v0.10.0` | refactor | refactor | PASS | 0 |  | 84 |
| `zendesk_source@v0.15.0` | refactor | refactor | not checked | 0 |  | 48 |
| `zendesk_source@v0.17.0-a1` | refactor | refactor | not checked | 0 |  | 53 |
| `zuora@v1.4.0` | refactor | refactor | PASS | 0 |  | 227 |

