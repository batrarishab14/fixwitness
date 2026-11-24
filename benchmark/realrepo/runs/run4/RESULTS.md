# Real-repository study: results

Run: `50657ac0543a9c9ac89723ff415e1ed782ed17ed study 2026-11-24T18:44:46Z only=`. Protocol: [PROTOCOL.md](PROTOCOL.md). Candidates: [candidates.csv](candidates.csv), frozen before any run. One run per candidate, defaults only (`fixwitness check --base <parent> --no-attacks --warehouse postgres://...`).

## Real bug fixes (would fixwitness have caught the bug?)

| Outcome | Count |
|---|---|
| FAIL | 31 |
| PASS | 32 |
| not checked | 8 |
| **checked** | **63** of 71 |

**Caught: 31/63 (49%) of the checked bug fixes** (FAIL: some valid generated input gives a different output before and after the fix).

| Label | Caught | Missed | Not checked |
|---|---|---|---|
| wrong-data | 28 | 26 | 4 |
| crash-on-data | 3 | 6 | 4 |

## Real refactors (does fixwitness raise false alarms?)

| Outcome | Count |
|---|---|
| PASS | 22 |
| FAIL | 2 |
| not checked | 15 |
| **checked** | **24** of 39 |

**False alarms: 0/24 (0%) of the checked refactors.** Of 2 FAILs, 0 are real differences, 0 false alarms, 2 not yet read.

| Refactor | Reading | What differs |
|---|---|---|
| `fivetran_log@v2.4.0-a1` | not yet read | If the file is sample as given, in `fivetran_platform__audit_table`, the output has 12 rows instead of 16; the row for 'this_connection' is missing. |
| `netsuite@v1.7.0` | not yet read | If `id` is the number 0, in `netsuite2__entity_subsidiary_relationships`, the output has 1 row instead of 1; a new row for 'test.netsuite2' appears. |

## Not checked, and why

| Candidate | Set | Why |
|---|---|---|
| `apple_store_source@v0.2.1` | bug | - / no sample for the dbt source(s) apple_store.sales_subscription_event_summary: put a CSV named after each table in the project's seeds/ or data/ folder, or pass --table sales_subscription_event_summary=FILE |
| `google_play_source@v0.1.1` | bug | - / no sample for the dbt source(s) google_play.stats_ratings_app_version, google_play.stats_ratings_country, google_play.stats_ratings_device, google_play.stats_ratings_os_version, google_play.stats_ratings_overview: pu |
| `google_play_source@v0.3.1` | bug | - / no sample for the dbt source(s) google_play.financial_stats_subscriptions_country, google_play.stats_crashes_app_version, google_play.stats_crashes_os_version, google_play.stats_crashes_overview, google_play.stats_in |
| `iterable@v1.6.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `iterable_source@v0.10.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `iterable_source@v0.4.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `klaviyo@v0.4.2` | refactor | the sources read the seeds from schema klaviyo, which no variable sets (in integration_tests/dbt_project.yml or as a package default), so they can't be pointed at a private schema in your warehouse |
| `marketo@v1.0.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `marketo@v1.4.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `marketo@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `mixpanel@v0.17.0` | refactor | `dbt parse` failed in integration_tests: [ERROR]: Encountered an error: / Compilation Error in model mixpanel__event (models/mixpanel__event.sql) / object of type 'bool' has no len() |
| `mixpanel@v0.17.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pardot@v1.4.2` | refactor | no dbt model's compiled SQL changed between the two versions |
| `pendo@v0.2.1` | bug | the sources read the seeds from schema pendo, which no variable sets (in integration_tests/dbt_project.yml or as a package default), so they can't be pointed at a private schema in your warehouse |
| `quickbooks@v0.12.3` | bug | no dbt model's compiled SQL changed between the two versions |
| `salesforce@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `shopify_source@v0.17.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `workday@v1.0.1` | bug | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v0.11.1` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk@v1.7.0` | refactor | no valid input could be compared (the original failed on all of them) |
| `zendesk@v1.9.0-a3` | bug | no valid input could be compared (the original failed on all of them) |
| `zendesk_source@v0.15.0` | refactor | no dbt model's compiled SQL changed between the two versions |
| `zendesk_source@v0.17.0-a1` | refactor | no dbt model's compiled SQL changed between the two versions |

## Every candidate

| Candidate | Set | Label | Outcome | Differences | Categories | Seconds |
|---|---|---|---|---|---|---|
| `apple_store@v0.3.2` | bug | wrong-data | FAIL | 50 | delimiter-mix empty unicode whitespace | 110 |
| `apple_store_source@v0.2.1` | bug | wrong-data | not checked | 0 |  | 84 |
| `fivetran_log@v0.5.4` | bug | wrong-data | PASS | 0 |  | 99 |
| `fivetran_log@v0.6.4` | bug | wrong-data | PASS | 0 |  | 68 |
| `fivetran_log@v0.7.1` | bug | wrong-data | PASS | 0 |  | 101 |
| `fivetran_log@v0.7.2` | bug | wrong-data | PASS | 0 |  | 84 |
| `fivetran_log@v1.2.0` | bug | wrong-data | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 129 |
| `fivetran_log@v1.4.1` | bug | crash-on-data | FAIL | 15 | csv-structure delimiter-mix long punctuation quotes shell-metachar unicode | 66 |
| `github@v0.5.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure flip long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 142 |
| `google_ads@v0.9.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate-row empty file-structure flip long null-column numeric-format pairs punctuation quotes schema shell-metachar time-edge unicode whitespace | 148 |
| `google_ads@v1.3.1` | bug | wrong-data | PASS | 0 |  | 96 |
| `google_ads_source@v0.9.3` | bug | wrong-data | PASS | 0 |  | 72 |
| `google_play_source@v0.1.1` | bug | wrong-data | not checked | 0 |  | 113 |
| `google_play_source@v0.3.1` | bug | wrong-data | not checked | 0 |  | 170 |
| `hubspot@v1.9.3` | bug | crash-on-data | PASS | 0 |  | 171 |
| `intercom@v0.9.1` | bug | wrong-data | PASS | 0 |  | 87 |
| `jira@v0.12.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 501 |
| `jira@v0.16.0` | bug | crash-on-data | PASS | 0 |  | 348 |
| `jira@v0.8.2` | bug | wrong-data | PASS | 0 |  | 461 |
| `jira@v1.3.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 247 |
| `klaviyo@v1.1.1` | bug | wrong-data | PASS | 0 |  | 78 |
| `klaviyo_source@v0.7.1` | bug | crash-on-data | PASS | 0 |  | 70 |
| `linkedin@v0.6.1` | bug | wrong-data | PASS | 0 |  | 106 |
| `linkedin_source@v0.8.2` | bug | wrong-data | PASS | 0 |  | 60 |
| `marketo@v0.9.1` | bug | wrong-data | PASS | 0 |  | 583 |
| `marketo_source@v0.7.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 106 |
| `netsuite@v0.6.3` | bug | wrong-data | PASS | 0 |  | 135 |
| `pendo@v0.2.1` | bug | crash-on-data | not checked | 0 |  | 24 |
| `quickbooks@v0.12.1` | bug | wrong-data | FAIL | 50 | date-format duplicate empty file-structure null-column numeric-format whitespace | 237 |
| `quickbooks@v0.12.2` | bug | wrong-data | PASS | 0 |  | 147 |
| `quickbooks@v0.12.3` | bug | crash-on-data | not checked | 0 |  | 68 |
| `quickbooks@v0.13.1` | bug | wrong-data | FAIL | 50 | case csv-structure date-format delimiter-mix duplicate duplicate-row empty file-structure flip long null-column numeric-format pairs punctuation quotes schema shell-metachar time-edge unicode whitespace | 233 |
| `quickbooks@v0.14.1` | bug | crash-on-data | PASS | 0 |  | 236 |
| `quickbooks@v0.15.0` | bug | wrong-data | FAIL | 2 | numeric-format whitespace | 153 |
| `quickbooks@v0.17.1` | bug | wrong-data | FAIL | 50 | case csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 210 |
| `quickbooks@v0.18.1` | bug | wrong-data | FAIL | 18 | case csv-structure date-format delimiter-mix flip long punctuation quotes shell-metachar unicode | 184 |
| `quickbooks@v0.19.0` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 289 |
| `quickbooks@v0.5.2` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 191 |
| `quickbooks@v0.5.3` | bug | wrong-data | PASS | 0 |  | 202 |
| `quickbooks@v0.8.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 196 |
| `quickbooks@v0.9.1` | bug | wrong-data | PASS | 0 |  | 158 |
| `quickbooks@v1.1.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 154 |
| `quickbooks@v1.2.1` | bug | wrong-data | FAIL | 1 | null-column | 271 |
| `quickbooks@v1.6.2` | bug | wrong-data | PASS | 0 |  | 180 |
| `quickbooks@v1.9.2` | bug | wrong-data | PASS | 0 |  | 249 |
| `sage_intacct@v0.5.0` | bug | wrong-data | FAIL | 50 | csv-structure date-format delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode | 144 |
| `salesforce@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 59 |
| `salesforce@v1.0.2` | bug | crash-on-data | PASS | 0 |  | 110 |
| `salesforce@v1.1.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes schema shell-metachar unicode | 143 |
| `shopify@v0.13.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long null-column numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 256 |
| `shopify@v0.16.1` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty long null-column numeric-format pairs punctuation quotes shell-metachar time-edge unicode whitespace | 116 |
| `shopify_source@v0.8.1` | bug | wrong-data | FAIL | 50 | delimiter-mix duplicate empty file-structure numeric-format schema whitespace | 136 |
| `shopify_source@v0.8.3` | bug | wrong-data | FAIL | 50 | delimiter-mix file-structure schema | 85 |
| `stripe@v0.14.1` | bug | crash-on-data | FAIL | 1 | numeric-format | 170 |
| `workday@v0.1.1` | bug | wrong-data | FAIL | 15 | empty flip null-column | 159 |
| `workday@v1.0.1` | bug | crash-on-data | not checked | 0 |  | 45 |
| `xero@v0.6.2` | bug | wrong-data | PASS | 0 |  | 140 |
| `zendesk@v0.13.1` | bug | wrong-data | PASS | 0 |  | 184 |
| `zendesk@v0.14.0` | bug | wrong-data | PASS | 0 |  | 134 |
| `zendesk@v0.22.0-a1` | bug | wrong-data | PASS | 0 |  | 215 |
| `zendesk@v0.25.0-a1` | bug | wrong-data | PASS | 0 |  | 115 |
| `zendesk@v0.8.1` | bug | wrong-data | PASS | 0 |  | 116 |
| `zendesk@v1.0.1` | bug | wrong-data | PASS | 0 |  | 181 |
| `zendesk@v1.5.1` | bug | wrong-data | PASS | 0 |  | 113 |
| `zendesk@v1.9.0-a3` | bug | wrong-data | not checked | 0 |  | 170 |
| `zendesk_source@v0.18.1` | bug | crash-on-data | FAIL | 2 | empty null-column | 70 |
| `zendesk_source@v0.18.2` | bug | crash-on-data | PASS | 0 |  | 103 |
| `zuora@v0.2.1` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 262 |
| `zuora@v0.3.2` | bug | wrong-data | FAIL | 50 | csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 236 |
| `zuora@v0.4.0` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long pairs punctuation quotes shell-metachar unicode whitespace | 174 |
| `zuora_source@v0.1.2` | bug | wrong-data | FAIL | 50 | case csv-structure delimiter-mix duplicate empty file-structure long numeric-format pairs punctuation quotes shell-metachar unicode whitespace | 147 |
| `asana@v1.4.0` | refactor | refactor | PASS | 0 |  | 110 |
| `fivetran_log@v1.0.1` | refactor | refactor | PASS | 0 |  | 111 |
| `fivetran_log@v2.2.2` | refactor | refactor | PASS | 0 |  | 88 |
| `fivetran_log@v2.4.0-a1` | refactor | refactor | FAIL | 50 | case delimiter-mix empty file-structure schema unicode whitespace | 132 |
| `fivetran_log@v2.5.2` | refactor | refactor | PASS | 0 |  | 97 |
| `github@v1.4.0` | refactor | refactor | PASS | 0 |  | 193 |
| `greenhouse@v1.4.0` | refactor | refactor | PASS | 0 |  | 151 |
| `hubspot@v0.5.2` | refactor | refactor | PASS | 0 |  | 115 |
| `hubspot@v1.8.0` | refactor | refactor | PASS | 0 |  | 238 |
| `intercom@v1.1.0` | refactor | refactor | PASS | 0 |  | 101 |
| `iterable@v1.5.0` | refactor | refactor | PASS | 0 |  | 88 |
| `iterable@v1.6.2` | refactor | refactor | not checked | 0 |  | 57 |
| `iterable_source@v0.10.2` | refactor | refactor | not checked | 0 |  | 39 |
| `iterable_source@v0.4.1` | refactor | refactor | not checked | 0 |  | 26 |
| `jira@v1.10.0` | refactor | refactor | PASS | 0 |  | 119 |
| `klaviyo@v0.4.2` | refactor | refactor | not checked | 0 |  | 9 |
| `mailchimp@v1.3.0` | refactor | refactor | PASS | 0 |  | 80 |
| `marketo@v1.0.1` | refactor | refactor | not checked | 0 |  | 52 |
| `marketo@v1.4.0` | refactor | refactor | not checked | 0 |  | 171 |
| `marketo@v1.4.2` | refactor | refactor | not checked | 0 |  | 45 |
| `mixpanel@v0.17.0` | refactor | refactor | not checked | 0 |  | 6 |
| `mixpanel@v0.17.2` | refactor | refactor | not checked | 0 |  | 30 |
| `netsuite@v1.7.0` | refactor | refactor | FAIL | 50 | duplicate empty numeric-format pairs whitespace | 242 |
| `pardot@v1.4.0` | refactor | refactor | PASS | 0 |  | 83 |
| `pardot@v1.4.2` | refactor | refactor | not checked | 0 |  | 54 |
| `quickbooks@v1.8.1` | refactor | refactor | PASS | 0 |  | 164 |
| `sage_intacct@v1.4.0` | refactor | refactor | PASS | 0 |  | 78 |
| `shopify_source@v0.17.0` | refactor | refactor | not checked | 0 |  | 43 |
| `shopify_source@v0.18.1` | refactor | refactor | PASS | 0 |  | 139 |
| `stripe_source@v0.7.4` | refactor | refactor | PASS | 0 |  | 80 |
| `stripe_source@v0.9.3` | refactor | refactor | PASS | 0 |  | 108 |
| `twilio@v1.4.0` | refactor | refactor | PASS | 0 |  | 74 |
| `zendesk@v0.11.1` | refactor | refactor | not checked | 0 |  | 50 |
| `zendesk@v0.21.0` | refactor | refactor | PASS | 0 |  | 123 |
| `zendesk@v1.7.0` | refactor | refactor | not checked | 0 |  | 121 |
| `zendesk_source@v0.10.0` | refactor | refactor | PASS | 0 |  | 80 |
| `zendesk_source@v0.15.0` | refactor | refactor | not checked | 0 |  | 55 |
| `zendesk_source@v0.17.0-a1` | refactor | refactor | not checked | 0 |  | 44 |
| `zuora@v1.4.0` | refactor | refactor | PASS | 0 |  | 226 |

