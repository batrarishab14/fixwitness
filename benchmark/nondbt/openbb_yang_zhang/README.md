# OpenBB Yang-Zhang volatility (a real non-dbt, pandas bug fix)

OpenBB PR #7807 (commit c6d097b27, Nov 2026) fixed `yang_zhang` in `openbb_technical/helpers.py`: the close
term used close-to-close returns, which already contain the overnight move, so overnight variance was counted
twice. This is a wrong-number bug in a widely used finance product, in pandas code, outside dbt.

Run (this is the fix direction, original = buggy, change = fix; `build.py` rebuilds the files from an OpenBB clone):

| Window | Result (verified, 27 Nov, fixwitness at PR #2 head) |
|---|---|
| 2 | FAIL: the fix changes output on 170 of 208 comparable inputs (38 identical, 48 not comparable) |
| 5 | FAIL, but only on the sample as given (1 of 208): fixwitness varies the first 3 rows, so a window of 5 leaves almost every case with no output |

On the 20-row sample the fix lowers the first value from 0.2782 to 0.2774 (0.3%): small, but on every row.

**Limits, stated plainly.** (1) This is a retrospective run on an already-fixed bug; no one found this bug with fixwitness.
(2) A rolling-window function must be run with a small window, because cases use the first 3 rows; the default
window of 30 would give no output. That is a fixwitness limitation for time-series code and needs a fix.
(3) The "Rows added or lost" wording in the report is misleading here: the row count is the same and only values changed.
