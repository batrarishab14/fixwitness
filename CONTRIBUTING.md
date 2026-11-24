# Contributing to fixwitness

Thank you for helping. The most valuable contribution is a **real change fixwitness judged wrongly**: a wrong change it passed, or a correct change it failed. Open an issue with the "missed a bug, or flagged a correct change" form; each one becomes a test.

## Set up

```bash
git clone https://github.com/batrarishab14/fixwitness && cd fixwitness
python -m unittest discover -s tests          # no dependencies needed
pip install duckdb sqlglot pandas polars pyarrow dbt-core dbt-duckdb   # optional: the tests that need them
```

Python 3.11 or newer. The core has no dependencies; keep it that way. Optional libraries are imported only where they are used.

## How the code is organised

| Module | What it does |
|---|---|
| `changes.py` | `fixwitness check` with no file: classifies every changed file and runs one check per item |
| `plan.py` | Turns settings into a plan: the two sides, how to run them, the sample data |
| `cases.py`, `sql.py`, `formats.py` | The generated inputs: CSV, tables (SQL, DataFrames), JSON and Parquet |
| `runner.py`, `sqlrun.py`, `pyrun.py`, `pyserve.py` | Running each side on each input |
| `compare.py` | Comparing two outputs |
| `core.py` | The check: cases, runs, comparison, verdict, proof |
| `shrink.py`, `explain.py` | The smallest input for a finding, and the sentence that explains it |
| `report.py`, `htmlreport.py` | report.md, report.html and reproductions |
| `dbtmode.py` | dbt projects compiled by dbt |
| `ui.py`, `setup.py`, `mcp_server.py`, `cli.py` | The local web app, `fixwitness setup`, the MCP server, the command line |

## Rules for changes that affect verdicts

A change to which inputs are generated or how outputs are compared changes evidence that other people rely on. Such a pull request:
1. re-runs the three benchmarks (`benchmark/run_bench.py`, `run_sql_bench.py`, `run_complex_bench.py`) and lists every result that changed;
2. describes the new inputs as a general rule (no rule that names a benchmark case);
3. adds a line to the development log of the current version in `study/`.

Results measured on the benchmarks are development results. Only the held-out evaluation in `study/PROTOCOL_*.md` is reported as an evaluation.

## Good first issues

- **A new kind of input value.** Add a category to `cases.py` (a value plus a one-line description of when real data contains it), with a test that shows a wrong change it catches.
- **A bug for the bug zoo.** A change that passes on today's data and differs on data you can describe; add it to `docs/BUG_ZOO.md` and the playground presets.
- **A dialect quirk.** A warehouse function sqlglot translates in a way that changes results on DuckDB; add a test in `DialectTests`.
- **Plain-English findings.** Improve a sentence in `explain.py` for a category whose wording is awkward.
- **More languages for scripts.** `program_for` in `plan.py` decides how a script is run; add one with a test.

## Style

Plain, short sentences in messages and docs. Every number in the README comes from a run whose log is in the repository or on the `ci-results` branch.
