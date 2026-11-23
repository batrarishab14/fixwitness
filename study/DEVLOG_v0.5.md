# fixwitness 0.5: development log

This log records every development run on the development set (the 92 existing fixes), including failures, as `PROTOCOL_v0.5.md` requires. These are development results. They do not measure how well 0.5 generalises; the held-out evaluation does that.

## Build 1 (23 November 2026)

**Change:** added the three input classes from the protocol: `schema`, `header-names` and `delimiter-mix`.

**Results against the protocol's criteria:**

| Criterion | Result |
|---|---|
| 1. All 7 wrong assistant fixes rejected | **Met:** 7/7. I05 ×3 rejected by `schema`; I07 by `header-names` (Claude, Gemini, Copilot) and `delimiter-mix` (ChatGPT) |
| 2. None of the 29 correct assistant fixes rejected | **Met:** 0/29 |
| 3. None of the 21 correct benchmark fixes rejected | **Not met:** 2/21. `S02-shell-eval/reference.sh` and `S03-shell-true/reference.py` changed output on 13 `delimiter-mix` inputs each |
| 4. At least 29/35 wrong benchmark fixes rejected | **Met:** 29/35 |
| 5. Unit tests pass; examples keep their verdicts | **Not met at first:** the safe fix in the `shell_eval` example failed for the same reason as S02 |

**Cause of the two false alarms:** S02, S03 and the `shell_eval` example are command-injection fixes. Their originals pass the field through a shell, which treats `;` and `|` as command separators and strips quotes. That behaviour is the vulnerability, so these cases put `shell-metachar` and `quotes` under review. `delimiter-mix` values are built from exactly those characters, but build 1 always graded them as `valid`, so the expected differences counted as failures.

## Build 2 (23 November 2026)

**Change:** a `delimiter-mix` value now follows the review setting of the categories its characters belong to.
- If it contains a shell metacharacter (`; | & $ * ? [ ] ~ # \ ` < > ( )`) and `shell-metachar` is under review, it is reviewed.
- If it contains a quote and `quotes` is under review, it is reviewed.
- Otherwise it stays `valid`. A value of tabs only, such as `a<TAB>b<TAB>c`, is still graded.

The rule depends only on the value's characters and the user's review list. No case or fix is special-cased. The `shell_eval` example's configuration is back to its 0.4.0 contents.

**Results:** see `benchmark/RESULTS.md` (written by build 2's run) and the summary added below when the run finishes.
