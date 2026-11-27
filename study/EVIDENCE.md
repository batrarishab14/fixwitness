# Evidence log

Every item below can be checked by a stranger from a public link. Status: **V** = re-verified on 27 Nov 2026 by
querying GitHub; **H** = taken from the project's own records (README / runs/run5), not re-verified here.

| # | Claim | Check it | Status |
|---|---|---|---|
| 1 | fixwitness 0.6 merged to main (PR #1) at 2026-11-27T03:04:17Z, merge commit 040cc09 | https://github.com/batrarishab14/fixwitness/pull/1 | V |
| 2 | CI on main (b5945cb) green: unit tests + real-data tests | runs 45932632509 (tests), 45932632493 (data) at https://github.com/batrarishab14/fixwitness/actions | V |
| 3 | A fix for a real bug in a live Fivetran package (dbt_zendesk, ticket #284: wrong unreplied-ticket count) is pushed on a fork with its integrity test. The PR to Fivetran is NOT submitted yet | branch `fix-unreplied-ticket-count`, commit b29ef3e: https://github.com/batrarishab14/dbt_zendesk/tree/fix-unreplied-ticket-count | V (branch exists); H (that it is the right bug) |
| 4 | Real-package study, run 5: 63 of 71 bug fixes checked; 22 of them (35%) confirmed as matching the release-note bug; 32 missed | benchmark/realrepo/runs/run5/RESULTS.md and results.csv | H |
| 5 | The misses are explained, case by case, from the real seed CSVs (9 checked, same cause: the data lacks the row the bug needs) | study/MISSED_BUGS.md | H |
| 6 | lever-43 is NOT counted as a catch: fixwitness found it only with hand-added seed rows | study/MISSED_BUGS.md | H |
| 7 | "Not exercisable with this data" check, checked on real dbt_quickbooks commits and seeds: v0.5.3 flagged (no Accounts Payable / Receivable / UndepositedFunds seed rows); 4 other silent PASSes and 1 refactor not flagged. Seeds only, not the full generated cases | benchmark/realrepo/exercise_validation/ (reproducible with the clone command in its README) | V |
| 8 | Study re-run with the check and the value-synthesis (catch rate and false alarms) | https://github.com/batrarishab14/fixwitness/actions/runs/45962989074 | PENDING: no numbers yet |

Not claimed: any catch rate beyond item 4, any second proven catch in a live package, any user adoption.
