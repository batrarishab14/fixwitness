# Real-repository study: summary

Five runs on the same frozen candidates (full tables, with why each candidate was not checked, in `runs/runN/RESULTS.md`).
"Flagged" = fixwitness reported a difference between the two versions. Each flag on a bug fix was read against the
release note (`runs/runN/bug_inspections.csv`).

| Run | What changed in fixwitness before it | Bug fixes flagged / checked | Refactors flagged / checked |
|---|---|---|---|
| 1 (first, counted) | - | 22 / 48 | 4 / 22 (2 real, 2 false alarms) |
| 2 | false alarms fixed (columns compared by name), more candidates run | 20 / 50 | 2 / 21 (both real) |
| 3 | the case cap shared fairly across kinds; focus ranked and limited to tables the change reads | 27 / 57 | 2 / 25 (both real) |
| 4 | seed column order kept; variables that enable edited models switched on | 31 / 63 | 2 / 25 (both real) |
| 5 | switch-on limited to plain on/off variables (a list variable broke mixpanel) | 31 / 63 | 2 / 25 (both real) |

Run 5, hand-read: of the 31 flagged bug fixes, 22 match the release note, 3 are in the model the note names, 4 are
unclear and 2 are not the bug. **Confirmed: 22 of 63 checked (35%); upper bound 31 of 63 (49%).**
Run 1's 22 were not read against the notes when counted.

Limits, measured: 32 bug fixes were missed (the seeds, varied, did not expose the bug); 8 bug fixes and 14 refactors
could not be checked (a fix that does not change compiled SQL, a source with no sample data, a seed schema no
variable sets). The same two refactors are flagged in every run after run 1, and are real differences.
