## What this changes

## How it was checked
- [ ] `python -m unittest discover -s tests` passes
- [ ] if it changes which inputs are generated or how outputs are compared: the benchmarks were re-run
      (`python benchmark/run_bench.py`, `benchmark/run_sql_bench.py`, `benchmark/run_complex_bench.py`)
      and every changed result is explained in the pull request
