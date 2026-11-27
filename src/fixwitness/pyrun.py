"""Command-line entry used by fixwitness to call one DataFrame function on one table bundle.

    python -m fixwitness.pyrun --function NAME [--library auto|pandas|polars|pyspark] [--ordered]
                               SCRIPT INPUT OUTPUT

The script is imported, each table of the bundle becomes a DataFrame of the chosen library, and the
function is called with them: by parameter name (name the tables after the parameters), or as its
only argument when there is one table. What it returns is written as CSV:
- a DataFrame (its index too, when the index has a name), a Series, a polars LazyFrame;
- a dict or tuple of DataFrames, as named outputs (compared one by one);
- a single value, as a one-cell table.

Exit codes: 0 success, 1 the function failed, 2 the script or the input could not be loaded.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import importlib.util
import inspect
import io
import math
import re
import sys
from pathlib import Path

from fixwitness.sql import SqlError, _cell, make_outputs, read_bundle, typed_rows

LIBRARIES = ("pandas", "polars", "pyspark")
_IMPORT = {lib: re.compile(rf"^\s*(?:from|import)\s+{lib}\b", re.M) for lib in LIBRARIES}


class FrameError(Exception):
    """The script, the function or the input could not be set up (exit code 2)."""


def detect_library(source: str) -> str:
    """The DataFrame library a script uses: pyspark or polars when it imports them, else pandas."""
    for lib in ("pyspark", "polars"):
        if _IMPORT[lib].search(source):
            return lib
    return "pandas"


def load_function(script: Path, name: str):
    spec = importlib.util.spec_from_file_location(f"fixwitness_user_{abs(hash(str(script)))}", script)
    if spec is None or spec.loader is None:
        raise FrameError(f"cannot import {script}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script.resolve().parent))  # the script's own imports
    spec.loader.exec_module(module)
    fn = getattr(module, name, None)
    if not callable(fn):
        raise FrameError(f"{script.name} has no function {name!r}")
    return fn


def arguments(fn, tables: list[str]) -> tuple[list, list[str]]:
    """How to call fn with the tables: (positional table names, keyword table names)."""
    params = [p for p in inspect.signature(fn).parameters.values()
              if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY, p.POSITIONAL_ONLY)]
    required = [p for p in params if p.default is p.empty]
    by_name = [p.name for p in params if p.name in tables]
    if required and all(p.name in tables for p in required) and not any(
            p.kind == p.POSITIONAL_ONLY for p in required):
        return [], by_name
    if len(tables) == 1 and len(required) == 1:
        return tables, []
    raise FrameError(f"cannot tell which table goes to which parameter of {fn.__name__}"
                     f"({', '.join(p.name for p in params)}): name the tables after the parameters "
                     f"(--table {required[0].name if required else 'NAME'}=FILE.csv); the tables are "
                     f"{', '.join(tables)}")


# ---------------------------------------------------------------- tables in

def _pandas_frame(name: str, text: str, types: dict):
    import pandas as pd
    header, kinds, _ = typed_rows(name, text, types)  # the same checks as SQL mode
    # The way pandas.read_csv loads the table, with the sample's date columns parsed and its text
    # columns kept as text (an ID such as 007 stays 007).
    dates = [c for c, k in zip(header, kinds) if k == "date"]
    dtype = {c: "str" for c, k in zip(header, kinds) if k == "text"}
    return pd.read_csv(io.StringIO(text), dtype=dtype, parse_dates=dates or False)


def _polars_frame(name: str, text: str, types: dict):
    import polars as pl
    header, kinds, rows = typed_rows(name, text, types)
    schema = {c: {"integer": pl.Int64, "number": pl.Float64, "date": pl.Date}.get(k, pl.String)
              for c, k in zip(header, kinds)}
    return pl.DataFrame(rows, schema=schema, orient="row")


_SPARK = None


def _spark():
    global _SPARK
    if _SPARK is None:
        from pyspark.sql import SparkSession
        _SPARK = (SparkSession.builder.master("local[1]").appName("fixwitness")
                  .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1")
                  .config("spark.sql.session.timeZone", "UTC").getOrCreate())
        _SPARK.sparkContext.setLogLevel("ERROR")
    return _SPARK


def _spark_frame(name: str, text: str, types: dict):
    from pyspark.sql import types as T
    header, kinds, rows = typed_rows(name, text, types)
    kind_type = {"integer": T.LongType(), "number": T.DoubleType(), "date": T.DateType()}
    schema = T.StructType([T.StructField(c, kind_type.get(k, T.StringType()), True) for c, k in zip(header, kinds)])
    return _spark().createDataFrame(rows, schema=schema)


FRAME = {"pandas": _pandas_frame, "polars": _polars_frame, "pyspark": _spark_frame}


# ---------------------------------------------------------------- results out

def _value(v):
    """A plain Python value from a library scalar; None for every kind of missing value."""
    if v is None:
        return None
    try:
        import numpy as np
        if isinstance(v, np.generic):
            v = v.item()
    except ImportError:
        pass
    if isinstance(v, float) and math.isnan(v):
        return None
    try:
        import pandas as pd
        if v is pd.NA or v is pd.NaT:
            return None
        if isinstance(v, pd.Timestamp):
            v = v.to_pydatetime()
    except ImportError:
        pass
    if isinstance(v, _dt.datetime) and v.tzinfo is None and v.time() == _dt.time(0):
        return v.date()  # a date held as a timestamp (pandas): written the same as a date
    return v


def _csv(header: list, rows: list[list], ordered: bool) -> bytes:
    cells = [[_cell(_value(v)) for v in r] for r in rows]
    if not ordered:
        cells.sort()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([str(h) for h in header])
    w.writerows(cells)
    return buf.getvalue().encode("utf-8")


def to_csv(result, ordered: bool) -> bytes:
    kind = type(result).__module__.split(".", 1)[0]
    if kind == "pandas":
        import pandas as pd
        if isinstance(result, pd.Series):
            result = result.to_frame(result.name if result.name is not None else "value")
        if isinstance(result, pd.DataFrame):
            if any(n is not None for n in result.index.names):
                result = result.reset_index()  # e.g. groupby keys
            header = ["/".join(map(str, c)) if isinstance(c, tuple) else c for c in result.columns]
            return _csv(header, result.astype(object).values.tolist(), ordered)
    if kind == "polars":
        import polars as pl
        if isinstance(result, pl.LazyFrame):
            result = result.collect()
        if isinstance(result, pl.Series):
            result = result.to_frame()
        if isinstance(result, pl.DataFrame):
            return _csv(result.columns, [list(r) for r in result.rows()], ordered)
    if kind == "pyspark" and hasattr(result, "collect") and hasattr(result, "columns"):
        return _csv(list(result.columns), [list(r) for r in result.collect()], ordered)
    if isinstance(result, (list, tuple)) and result and all(_is_frame(r) for r in result):
        return make_outputs({str(i): to_csv(r, ordered) for i, r in enumerate(result)})
    if isinstance(result, dict) and result and all(_is_frame(r) for r in result.values()):
        return make_outputs({str(k): to_csv(r, ordered) for k, r in result.items()})
    if _is_frame(result):
        raise FrameError(f"cannot write a {type(result).__name__} as a table")
    return _csv(["value"], [[result]], True)


def _is_frame(x) -> bool:
    if type(x).__module__.split(".", 1)[0] not in ("pandas", "polars", "pyspark"):
        return False
    return hasattr(x, "columns") or type(x).__name__ in ("Series", "LazyFrame")


def prepare_call(script: Path, function: str, bundle: bytes, library: str = "auto"):
    """Import the script and build its DataFrames: (function, positional args, keyword args, library)."""
    lib = detect_library(script.read_text(encoding="utf-8")) if library == "auto" else library
    if lib not in LIBRARIES:
        raise FrameError(f"unknown library {library!r}; use auto, pandas, polars or pyspark")
    try:
        __import__(lib)
    except ImportError:
        raise FrameError(f"{script.name} uses {lib}, which is not installed") from None
    tables, types = read_bundle(bundle)
    fn = load_function(script, function)
    positional, keyword = arguments(fn, list(tables))
    frames = {name: FRAME[lib](name, text, types) for name, text in tables.items()}
    return fn, [frames[n] for n in positional], {n: frames[n] for n in keyword}, lib


def run_function(script: Path, function: str, bundle: bytes, library: str = "auto", ordered: bool = False) -> bytes:
    fn, args, kwargs, _ = prepare_call(script, function, bundle, library)
    return to_csv(fn(*args, **kwargs), ordered)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fixwitness.pyrun")
    ap.add_argument("--function", required=True)
    ap.add_argument("--library", default="auto", choices=("auto",) + LIBRARIES)
    ap.add_argument("--ordered", action="store_true")
    ap.add_argument("script")
    ap.add_argument("input")
    ap.add_argument("output")
    a = ap.parse_args(argv)
    try:
        try:
            fn, args, kwargs, _ = prepare_call(Path(a.script), a.function, Path(a.input).read_bytes(), a.library)
        except (FrameError, SqlError, OSError) as exc:
            print(f"fixwitness.pyrun: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # the script failed while being imported, or a table did not load
            print(f"fixwitness.pyrun: could not set up: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        try:
            out = to_csv(fn(*args, **kwargs), a.ordered)
        except FrameError as exc:
            print(f"fixwitness.pyrun: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # the user's function failed on this input
            print(f"fixwitness.pyrun: {a.function} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
    finally:
        if _SPARK is not None:
            _SPARK.stop()
    Path(a.output).write_bytes(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
