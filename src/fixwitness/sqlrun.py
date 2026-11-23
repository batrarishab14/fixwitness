"""Command-line entry used by fixwitness to run one SQL query on one table bundle.

    python -m fixwitness.sqlrun [--engine auto|duckdb|sqlite] [--dbt auto|on|off] [--ordered] QUERY INPUT OUTPUT

Exit codes: 0 success, 1 the query failed, 2 the input could not be loaded or the model could not be rendered.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fixwitness.sql import SqlError, run_query


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fixwitness.sqlrun")
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--dbt", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--ordered", action="store_true")
    ap.add_argument("query")
    ap.add_argument("input")
    ap.add_argument("output")
    a = ap.parse_args(argv)
    try:
        sql = Path(a.query).read_text(encoding="utf-8")
        out = run_query(sql, Path(a.input).read_bytes(), a.engine, a.dbt, a.ordered)
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
