"""Command-line entry used by fixwitness to run one SQL query on one table bundle.

    python -m fixwitness.sqlrun [--engine E] [--dbt auto|on|off] [--dialect D] [--outputs a,b] [--ordered]
                                QUERY INPUT OUTPUT

QUERY is a .sql file, or a folder of .sql models (a pipeline).

Exit codes: 0 success, 1 the query failed, 2 the input could not be loaded or the model could not be rendered.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fixwitness.sql import SqlError, run_pipeline, run_query


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fixwitness.sqlrun")
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--dbt", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--ordered", action="store_true")
    ap.add_argument("--dialect", default=None)
    ap.add_argument("--outputs", default=None)
    ap.add_argument("query")
    ap.add_argument("input")
    ap.add_argument("output")
    a = ap.parse_args(argv)
    try:
        data = Path(a.input).read_bytes()
        outputs = [o.strip() for o in a.outputs.split(",") if o.strip()] if a.outputs else None
        if Path(a.query).is_dir():
            out = run_pipeline(Path(a.query), data, a.engine, a.dbt, a.ordered, a.dialect, outputs)
        else:
            out = run_query(Path(a.query).read_text(encoding="utf-8"), data, a.engine, a.dbt, a.ordered, a.dialect)
    except SqlError as exc:
        print(f"fixwitness.sqlrun: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # the engine's own error: the query failed on this input
        print(f"fixwitness.sqlrun: query failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    Path(a.output).write_bytes(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
