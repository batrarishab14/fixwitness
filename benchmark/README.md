# fixwitness benchmark

**Question:** when an automated fix is wrong, which checks catch it?

**Setup:**
- 20 small data jobs (Python and shell), each with a sample of normal data and one task:
  - **security**: 5 cases (CWE-95, CWE-78 twice, CWE-1336, CWE-22);
  - **incident**: 9 cases (the job broke on new input: thousands separators, accounting negatives, a date-format change, `N/A` markers, a renamed column, a UTF-8 BOM, semicolon delimiters, decimal commas, percentages);
  - **refactor**: 6 cases (rounding, sort keys, de-duplication, number formatting, case folding, integer division).
- 56 fixes in total: 21 correct (one reference per case, plus one alternative) and 35 wrong.

Each wrong fix models a documented failure pattern: over-broad normalisation, silently dropped rows, defaults that hide bad values, lost signs, stricter parsers, changed rounding or formatting, over-correction, and incomplete security fixes. The pattern is named on the second line of every fix file.

## Results

Full table: [RESULTS.md](RESULTS.md). Raw data: `results.csv`. fixwitness 0.4.0.

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| Job runs (what "pipeline is green" or `dbt build` checks) | 3/35 (9%) | 0/21 |
| Sample regression test (output on the sample unchanged) | 6/35 (17%) | 0/21 |
| **fixwitness** | **29/35 (83%)** | **0/21** |
| **fixwitness + expected output for the incident** | **35/35 (100%)** | **0/21** |

**The 6 wrong fixes plain fixwitness accepts** are all incident repairs that process the bad input with a plausible but wrong value: a refund that loses its minus sign, a 0 instead of N/A, a decimal comma read as a thousands separator, a percentage not divided by 100. Nothing in the original's behaviour on normal data says what the right answer is, so they are caught only when the expected output for the incident is given (`--incident-expected`). Repairs that *drop* the bad rows are caught without it, because the original always writes one row per input row.

## Threats to validity (read before citing)

- **The wrong fixes are synthetic.** They model failure patterns. None was produced by an AI agent, so the detection rates are not rates for any agent. For real assistant fixes, see the study in [`../study/`](../study/README.md): of 36 fixes by four assistants, 7 were wrong and fixwitness 0.4.0 accepted all 36.
- **The tool's author also wrote the benchmark.** While designing the cases, the input catalogue was extended with dates, duplicate keys, rounding edges (`0.125`, `2.675`), `ß`/`İ` and `;`. A benchmark built independently could find more blind spots.
- **Scale.** 20 cases and 56 fixes in small, single-file jobs, all CSV in and CSV out.
- **Ground truth.** For incidents, the expected output is the reference repair's output, reviewed by hand.
- **One reference was corrected after the assistant study.** The I07 reference decided the delimiter from the first physical line and failed on a contrived header; it now reads the file as before and retries with `;` only on failure. No benchmark result changed (the previous version is described in `study/run_notes.md`).

## Run it

```bash
python3 benchmark/run_bench.py            # about 2 minutes; writes results.csv and RESULTS.md
```

## Measure real agents

1. Run `python3 benchmark/run_bench.py prompts`. It writes `cases/<id>/PROMPT.md`: the task, the files and the original code.
2. Give each prompt to an agent (Claude Code, GitHub Copilot, Cursor, Codex and so on) in a clean session. Accept its answer unchanged.
3. Save the fixed file as `agents/<agent-name>/<case-id>/<any-name>.py` (or `.sh`).
4. Run `python3 benchmark/run_bench.py`. Agent fixes appear in their own table with fixwitness's verdict and reason.
5. **Review every agent fix by hand** to label it correct or wrong. That label is the ground truth for an agent study; fixwitness's verdict is what you measure against it.

Record the agent, model, version and date for each run. Results change between model versions.

## Add a case

Create `cases/<id>/` containing:
- `case.toml`: title, kind, finding, script, run, columns, review, task, and for incidents `incident` and `expected`;
- `original.py` or `original.sh`;
- `sample.csv`;
- for incidents, `incident.csv` and `expected.csv`;
- `fixes/`, with one file per fix whose first two lines are `# label: correct|wrong` and `# pattern: ...`.
