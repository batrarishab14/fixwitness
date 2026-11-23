# fixwitness benchmark results

fixwitness 0.5.0 · 92 fixes across 20 cases (21 correct, 35 wrong, plus 36 assistant fixes) · run time 330s

The wrong fixes are **synthetic**. Each models a documented failure pattern (named per fix below); none were produced by an AI agent. Fixes written by AI assistants are listed separately at the end.

## Headline

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| job runs | 3/35 (9%) | 0/21 (0%) |
| sample test | 6/35 (17%) | 0/21 (0%) |
| fixwitness | 29/35 (83%) | 0/21 (0%) |
| fixwitness+exp | 35/35 (100%) | 0/21 (0%) |

`fixwitness+exp` gives fixwitness the correct output for the incident input; it differs from `fixwitness` only for incident cases.

## By kind

| Kind | Wrong fixes | Caught by: job runs | sample test | fixwitness | fixwitness+exp |
|---|---|---|---|---|---|
| security | 9 | 0 | 1 | 9 | 9 |
| incident | 20 | 3 | 3 | 14 | 20 |
| refactor | 6 | 0 | 2 | 6 | 6 |

## Where fixwitness is blind

Wrong fixes that plain fixwitness accepted (no expected output):

- `I01-thousands-separator/default_zero.py`: silent wrong value: unparseable amounts become 0. caught when the expected output is given.
- `I02-accounting-negatives/strip_parens.py`: sign lost: parentheses removed, refund becomes a charge. caught when the expected output is given.
- `I04-null-markers/default_zero.py`: silent wrong value: N/A becomes quantity 0 (total 0.00). caught when the expected output is given.
- `I05-renamed-column/default_zero.py`: silent wrong value: a missing column becomes 0. caught when the expected output is given.
- `I08-decimal-comma/remove_commas.py`: wrong interpretation: treating the comma as a thousands separator makes 125,50 into 12550. caught when the expected output is given.
- `I09-percent-rates/strip_percent.py`: unit error: stripping % without dividing by 100 makes the fee 100x. caught when the expected output is given.

False alarms on correct fixes:

- none

## Every fix

| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | +exp | Score |
|---|---|---|---|---|---|---|---|---|
| I01-thousands-separator | default_zero.py | wrong | silent wrong value: unparseable amounts become 0 | accept | accept | accept | **reject** | 0 |
| I01-thousands-separator | reference.py | correct | accept thousands separators only; everything else parsed as before | accept | accept | accept | accept | 96 |
| I01-thousands-separator | skip_bad_rows.py | wrong | silent data loss: rows that fail to parse are skipped | accept | accept | **reject** | **reject** | 0 |
| I01-thousands-separator | strip_non_digits.py | wrong | over-broad normalisation: keeping only digits and dots drops minus signs | accept | accept | **reject** | **reject** | 0 |
| I02-accounting-negatives | reference.py | correct | (x) means -x; everything else parsed as before | accept | accept | accept | accept | 96 |
| I02-accounting-negatives | regex_clean.py | wrong | over-broad normalisation: regex clean-up changes 1e3 and drops the refund sign | accept | accept | **reject** | **reject** | 0 |
| I02-accounting-negatives | strip_parens.py | wrong | sign lost: parentheses removed, refund becomes a charge | accept | accept | accept | **reject** | 0 |
| I03-date-format-drift | fromisoformat.py | wrong | stricter parser: fromisoformat rejects unpadded dates the job accepted | accept | accept | **reject** | **reject** | 0 |
| I03-date-format-drift | reference.py | correct | accept both formats strictly | accept | accept | accept | accept | 95 |
| I03-date-format-drift | skip_bad_rows.py | wrong | silent data loss: rows with other date formats are skipped | accept | accept | **reject** | **reject** | 0 |
| I03-date-format-drift | string_slice.py | wrong | parsing replaced by string slicing: unpadded dates give wrong months | accept | accept | **reject** | **reject** | 0 |
| I04-null-markers | default_zero.py | wrong | silent wrong value: N/A becomes quantity 0 (total 0.00) | accept | accept | accept | **reject** | 0 |
| I04-null-markers | isdigit.py | wrong | over-broad check: isdigit() also turns returns (-1) and padded values into 0 | accept | accept | **reject** | **reject** | 0 |
| I04-null-markers | reference.py | correct | N/A means unknown: leave total empty; everything else as before | accept | accept | accept | accept | 95 |
| I04-null-markers | skip_bad_rows.py | wrong | silent data loss: rows with N/A are skipped | accept | accept | **reject** | **reject** | 0 |
| I05-renamed-column | default_zero.py | wrong | silent wrong value: a missing column becomes 0 | accept | accept | accept | **reject** | 0 |
| I05-renamed-column | positional.py | wrong | fragile: reads the third column by position, which is now 'currency' | **reject** | **reject** | **reject** | **reject** | 0 |
| I05-renamed-column | reference.py | correct | read 'amount' or, when absent, 'amount_usd' | accept | accept | accept | accept | 96 |
| I06-utf8-bom | ascii_ignore.py | wrong | data loss: decoding as ASCII with errors ignored deletes accented letters | accept | accept | **reject** | **reject** | 0 |
| I06-utf8-bom | reference.py | correct | read with utf-8-sig, which drops a leading BOM | accept | accept | accept | accept | 98 |
| I06-utf8-bom | strip_keys.py | wrong | ineffective: str.strip() does not remove a BOM | **reject** | **reject** | **reject** | **reject** | 0 |
| I07-semicolon-delimiter | always_semicolon.py | wrong | regression: hard-coding ';' breaks every existing comma file | **reject** | **reject** | **reject** | **reject** | 0 |
| I07-semicolon-delimiter | reference.py | correct | read the file exactly as before; only if that fails, read it again with ';' | accept | accept | accept | accept | 98 |
| I07-semicolon-delimiter | replace_text.py | wrong | data corruption: replacing ';' everywhere also splits values that contain ';' | accept | accept | **reject** | **reject** | 0 |
| I08-decimal-comma | reference.py | correct | a single comma followed by 1-2 digits is a decimal comma | accept | accept | accept | accept | 96 |
| I08-decimal-comma | remove_commas.py | wrong | wrong interpretation: treating the comma as a thousands separator makes 125,50 into 12550 | accept | accept | accept | **reject** | 0 |
| I09-percent-rates | reference.py | correct | '12%' means 0.12; everything else as before | accept | accept | accept | accept | 96 |
| I09-percent-rates | regex_clean.py | wrong | over-broad normalisation: regex clean-up drops minus signs and exponents | accept | accept | **reject** | **reject** | 0 |
| I09-percent-rates | strip_percent.py | wrong | unit error: stripping % without dividing by 100 makes the fee 100x | accept | accept | accept | **reject** | 0 |
| R01-rounding | builtin_round.py | wrong | rounding change: float round() is not half-up (2.675 -> 2.67, 0.125 -> 0.12) | accept | accept | **reject** | **reject** | 0 |
| R01-rounding | reference.py | correct | same Decimal half-up rounding, moved into a helper | accept | accept | accept | accept | 96 |
| R02-sort-order | reference.py | correct | same key, named function | accept | accept | accept | accept | 96 |
| R02-sort-order | string_sort.py | wrong | ordering change: amounts compared as text ('9.5' > '10.0') | accept | **reject** | **reject** | **reject** | 0 |
| R03-dedupe | dict_comprehension.py | wrong | semantics change: a dict comprehension keeps the last duplicate, not the first | accept | accept | **reject** | **reject** | 0 |
| R03-dedupe | reference.py | correct | keep the first row per id, via dict.setdefault | accept | accept | accept | accept | 97 |
| R04-number-format | reference.py | correct | format() with the same spec | accept | accept | accept | accept | 96 |
| R04-number-format | str_round.py | wrong | formatting change: str(round()) drops trailing zeros (7.50 -> 7.5) | accept | **reject** | **reject** | **reject** | 0 |
| R05-case-folding | casefold.py | wrong | key change: casefold() turns 'Straße' into 'strasse', breaking joins on existing keys | accept | accept | **reject** | **reject** | 0 |
| R05-case-folding | reference.py | correct | same lower(), moved into a helper | accept | accept | accept | accept | 97 |
| R06-integer-division | floor_division.py | wrong | rounding change: // floors, so negative totals (refunds) round the other way | accept | accept | **reject** | **reject** | 0 |
| R06-integer-division | reference.py | correct | math.trunc keeps truncation towards zero | accept | accept | accept | accept | 95 |
| S01-eval-amount | float.py | wrong | type change: whole numbers become floats (1200 -> 1200.0) | accept | accept | **reject** | **reject** | 0 |
| S01-eval-amount | reference.py | correct | parse numeric literals without executing code; integers stay integers | accept | accept | accept | accept | 96 |
| S01-eval-amount | strict_allowlist.py | wrong | allowlist too strict: valid formats such as 1e3 or +7 are rejected | accept | accept | **reject** | **reject** | 0 |
| S01-eval-amount | use_decimal.py | wrong | formatting change: Decimal keeps trailing zeros (12.5 -> 12.50) | accept | **reject** | **reject** | **reject** | 0 |
| S02-shell-eval | quote_inside_eval.sh | wrong | incomplete fix: quoting inside eval still runs $(...) | accept | accept | **reject** | **reject** | 0 |
| S02-shell-eval | reference.sh | correct | no eval; keep the trim-and-collapse behaviour eval gave for free | accept | accept | accept | accept | 95 |
| S02-shell-eval | remove_eval.sh | wrong | behaviour loss: removing eval also removes whitespace trimming | accept | accept | **reject** | **reject** | 0 |
| S03-shell-true | reference.py | correct | no shell; reproduce echo's whitespace collapsing and tr's ASCII-only upper-casing | accept | accept | accept | accept | 95 |
| S03-shell-true | shlex_quote.py | wrong | behaviour change: quoting the value stops echo from collapsing whitespace | accept | accept | **reject** | **reject** | 0 |
| S03-shell-true | str_upper.py | wrong | semantic drift: Unicode-aware upper() and no whitespace collapsing | accept | accept | **reject** | **reject** | 0 |
| S04-template-eval | html_escape.py | wrong | over-correction: HTML-escaping changes quotes and ampersands in plain text | accept | accept | **reject** | **reject** | 0 |
| S04-template-eval | reference.py | correct | stop evaluating templates; data is treated as text | accept | accept | accept | accept | 97 |
| S05-path-traversal | basename.py | correct | alternative fix: keep only the last path component | accept | accept | accept | accept | 97 |
| S05-path-traversal | reference.py | correct | reject names containing a path separator | accept | accept | accept | accept | 97 |
| S05-path-traversal | sanitize_all.py | wrong | over-correction: replacing every non-alphanumeric character renames valid customers | accept | accept | **reject** | **reject** | 0 |

## Assistant fixes

Labels come from `study/labels.csv` (code review; see `study/README.md`). They are not used in the headline above.

| Agent | Case | Label | Job runs | Sample test | fixwitness | +exp | Score | Reason |
|---|---|---|---|---|---|---|---|---|
| chatgpt-r1 | I01-thousands-separator | correct | accept | accept | accept | accept | 96 | - |
| claude-r1 | I01-thousands-separator | correct | accept | accept | accept | accept | 96 | - |
| copilot-r1 | I01-thousands-separator | correct | accept | accept | accept | accept | 96 | - |
| gemini-r1 | I01-thousands-separator | correct | accept | accept | accept | accept | 96 | - |
| chatgpt-r1 | I02-accounting-negatives | correct | accept | accept | accept | accept | 96 | - |
| claude-r1 | I02-accounting-negatives | correct | accept | accept | accept | accept | 96 | - |
| copilot-r1 | I02-accounting-negatives | correct | accept | accept | accept | accept | 96 | - |
| gemini-r1 | I02-accounting-negatives | correct | accept | accept | accept | accept | 96 | - |
| chatgpt-r1 | I03-date-format-drift | correct | accept | accept | accept | accept | 95 | - |
| claude-r1 | I03-date-format-drift | correct | accept | accept | accept | accept | 95 | - |
| copilot-r1 | I03-date-format-drift | correct | accept | accept | accept | accept | 95 | - |
| gemini-r1 | I03-date-format-drift | correct | accept | accept | accept | accept | 95 | - |
| chatgpt-r1 | I04-null-markers | correct | accept | accept | accept | accept | 95 | - |
| claude-r1 | I04-null-markers | correct | accept | accept | accept | accept | 95 | - |
| copilot-r1 | I04-null-markers | correct | accept | accept | accept | accept | 95 | - |
| gemini-r1 | I04-null-markers | correct | accept | accept | accept | accept | 95 | - |
| chatgpt-r1 | I05-renamed-column | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 2 valid inputs |
| claude-r1 | I05-renamed-column | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 2 valid inputs |
| copilot-r1 | I05-renamed-column | correct | accept | accept | accept | accept | 96 | - |
| gemini-r1 | I05-renamed-column | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 2 valid inputs |
| chatgpt-r1 | I06-utf8-bom | correct | accept | accept | accept | accept | 98 | - |
| claude-r1 | I06-utf8-bom | correct | accept | accept | accept | accept | 98 | - |
| copilot-r1 | I06-utf8-bom | correct | accept | accept | accept | accept | 98 | - |
| gemini-r1 | I06-utf8-bom | correct | accept | accept | accept | accept | 98 | - |
| chatgpt-r1 | I07-semicolon-delimiter | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 1 valid inputs |
| claude-r1 | I07-semicolon-delimiter | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 3 valid inputs |
| copilot-r1 | I07-semicolon-delimiter | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 1 valid inputs |
| gemini-r1 | I07-semicolon-delimiter | wrong | accept | accept | **reject** | **reject** | 0 | the fix changes output on 3 valid inputs |
| chatgpt-r1 | I08-decimal-comma | correct | accept | accept | accept | accept | 96 | - |
| claude-r1 | I08-decimal-comma | correct | accept | accept | accept | accept | 96 | - |
| copilot-r1 | I08-decimal-comma | correct | accept | accept | accept | accept | 96 | - |
| gemini-r1 | I08-decimal-comma | correct | accept | accept | accept | accept | 96 | - |
| chatgpt-r1 | I09-percent-rates | correct | accept | accept | accept | accept | 96 | - |
| claude-r1 | I09-percent-rates | correct | accept | accept | accept | accept | 96 | - |
| copilot-r1 | I09-percent-rates | correct | accept | accept | accept | accept | 96 | - |
| gemini-r1 | I09-percent-rates | correct | accept | accept | accept | accept | 96 | - |
