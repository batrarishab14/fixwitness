# Assistant study: fixes written by AI assistants

On 20 November 2026 the nine incident tasks (I01–I09) were given to four chat assistants, one run each, with all nine tasks in one prompt.

| File | What it is |
|---|---|
| `PROMPT_incidents.txt` | The prompt, sent unchanged to every assistant |
| `runs_raw/` | Every answer exactly as pasted, including the copies that were damaged |
| `run_notes.md` | What happened in each run, which copies were discarded and why |
| `runs.txt` | The answers used, each under a `RUN | assistant | model | run | date` line |
| `import_runs.py` | Turns `runs.txt` into `benchmark/agents/<assistant>-r1/<case>/fix.py` and writes `runs_index.csv` |
| `labels.csv` | Correct or wrong for each of the 36 fixes, with the reason |
| `label_check.py` | Runs the original and each fix on 2,860 hand-written and random inputs (529 of which the original handles) and lists every handled input whose output the fix changes; output in `label_check_output.txt`. `python3 study/label_check.py references` applies the same check to the benchmark's reference repairs |

## Results

All 36 fixes produce the expected output on the incident input and pass every check: the job runs, the output on the sample is unchanged, and fixwitness passes them with and without the expected output.

The rule for every label is the task's own: process the incident input correctly **without changing the output for any input the job already handled**. By this rule, 7 fixes are wrong:

| Fixes | What changes | Example input the original handled | Plausible? |
|---|---|---|---|
| I05: ChatGPT, Claude, Gemini | `amount_usd` is read in preference to `amount` | `payment_id,customer,amount,amount_usd` / `P-1,Acme,12.50,13.75`: original 1250, fix 1375 | yes, e.g. during a migration |
| I07: ChatGPT | `csv.Sniffer` picks `;` when a text value mixes `;` and quotes | `payment_id,customer,amount,note` / `P-1,Acme,12.50,call back; "urgent"`: original 1250, fix fails | yes |
| I07: Claude, Gemini | `;` is chosen when the first line has more semicolons than commas | `payment_id,customer,amount,;;;;` / `P-1,Acme,12.50,x`: original 1250, fix fails | no, contrived header |
| I07: Copilot | the delimiter is decided from the first physical line, not the header record | `"a;` (newline) `b",payment_id,customer,amount` / `z,P-1,Acme,12.50`: original 1250, fix fails | no, contrived header |

fixwitness 0.4.0 accepted all seven:
- six need a different header, which it never varies;
- the seventh (ChatGPT, I07) is triggered by a cell value that combines `;` and quotes, which its catalogue lacks.

The labels were proposed with an AI assistant (Claude, which is also one of the assistants studied). That is why every wrong label cites an input that reproduces the difference. An independent review found the ChatGPT and Copilot I07 inputs; those patterns were then added to `label_check.py`.

## Copying problems, and what was done

- **ChatGPT:** the copy lost every line break, twice. They were restored only where this is exact: indented lines are split where their preserved indentation starts, top-level lines must match the original program's, and removing the restored breaks gives back the pasted text character for character. Nothing else was changed.
- **Copilot:** the first copies lost all indentation, which cannot be restored without guessing. The fixes were then copied with each code block's copy button; that copy matches the earlier one line for line apart from indentation.
- **Gemini, Claude:** a "Python" label line above each block and Claude's notes after the last task were dropped. The code is unchanged.

## Reproduce

```bash
python3 study/import_runs.py study/runs.txt   # writes benchmark/agents/
python3 study/label_check.py                   # about 2 seconds
python3 benchmark/run_bench.py                 # about 3 minutes; agent fixes are listed in RESULTS.md
```
