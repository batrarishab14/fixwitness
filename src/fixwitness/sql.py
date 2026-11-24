"""SQL and dbt models: load tables, run a query, write the result as CSV.

fixwitness checks a SQL change the same way it checks a script: it runs the original query and
the changed query on the same generated tables and compares the results. A case is one set of
tables, stored as a small JSON "bundle":

    {"fixwitness_tables": 1,
     "types":  {"orders": {"id": "integer", "amount": "number", "day": "date", "note": "text"}},
     "tables": {"orders": "id,amount,day,note\\n1,12.50,2026-01-02,x\\n"}}

Column types come from the user's sample tables, so every case is loaded with the same schema.
An empty cell is loaded as NULL. A value that does not fit its column's type (for example
"1,250" in a numeric column) fails the load, as a warehouse would reject it, and the case is
reported as "not comparable".

Engines: DuckDB when it is installed (`pip install duckdb`), else SQLite from the standard
library. Both sides of a check always use the same engine.

dbt models: `{{ ref('x') }}` and `{{ source('s', 'x') }}` become table `x`, and `{{ config(...) }}`
is removed. Models that use other Jinja (macros, `{% if %}`, `{{ this }}`) are refused with a
clear message; compile them with `dbt compile` and check the compiled SQL instead.

Pipelines: when QUERY is a folder, every .sql file in it is a model named after the file. Models
run in dependency order (from ref() and from the tables named after FROM and JOIN), each as
CREATE TABLE <model> AS <query>, and every model's result is written to one "outputs" bundle:

    {"fixwitness_outputs": 1, "outputs": {"stg_orders": "<csv>", "revenue": "<csv>"}}

Warehouse dialects: with a dialect (snowflake, bigquery, databricks, ...), each query is
translated to the local engine's SQL with sqlglot (pip install sqlglot) before it runs.

Run as: python -m fixwitness.sqlrun [--engine auto|duckdb|sqlite] [--dialect D] [--outputs a,b] [--ordered] QUERY INPUT OUTPUT
"""

from __future__ import annotations

import csv
import datetime as _dt
import decimal
import io
import json
import re
from pathlib import Path

BUNDLE_KEY = "fixwitness_tables"
OUTPUTS_KEY = "fixwitness_outputs"
_NUMBER = re.compile(r"\s*[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*")
_INTEGER = re.compile(r"\s*[+-]?\d+\s*")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_REF = re.compile(r"\{\{\s*ref\(\s*(['\"])([^'\"]+)\1\s*(?:,\s*(['\"])([^'\"]+)\3\s*)?(?:,\s*v(?:ersion)?\s*=\s*[^)]*)?\)\s*\}\}")
_SOURCE = re.compile(r"\{\{\s*source\(\s*(['\"])([^'\"]+)\1\s*,\s*(['\"])([^'\"]+)\3\s*\)\s*\}\}")
_CONFIG = re.compile(r"\{\{\s*config\(.*?\)\s*\}\}", re.DOTALL)
_JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)


class SqlError(ValueError):
    pass


# ---------------------------------------------------------------- bundles

def make_bundle(tables: dict[str, bytes], types: dict[str, dict[str, str]]) -> bytes:
    body = {BUNDLE_KEY: 1, "types": types,
            "tables": {name: data.decode("utf-8-sig") for name, data in tables.items()}}
    return json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")


def read_bundle(data: bytes) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    try:
        body = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SqlError(f"input is not a fixwitness table bundle: {exc}") from exc
    if not isinstance(body, dict) or body.get(BUNDLE_KEY) != 1:
        raise SqlError("input is not a fixwitness table bundle")
    return body["tables"], body.get("types", {})


def is_bundle(data: bytes | None) -> bool:
    return bool(data) and data.lstrip()[:1] == b"{" and BUNDLE_KEY.encode() in data[:200]


def make_outputs(outputs: dict[str, bytes]) -> bytes:
    body = {OUTPUTS_KEY: 1, "outputs": {k: v.decode("utf-8") for k, v in outputs.items()}}
    return json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")


def read_outputs(data: bytes | None) -> dict[str, bytes] | None:
    """The named outputs of a pipeline run, or None if `data` is a single output."""
    if not data or data.lstrip()[:1] != b"{" or OUTPUTS_KEY.encode() not in data[:200]:
        return None
    try:
        body = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict) or body.get(OUTPUTS_KEY) != 1:
        return None
    return {k: v.encode("utf-8") for k, v in body.get("outputs", {}).items()}


# ---------------------------------------------------------------- dbt

def render_dbt(sql: str) -> str:
    """Resolve ref/source/config in a single dbt model; refuse anything else."""
    out = _JINJA_COMMENT.sub("", sql)
    out = _CONFIG.sub("", out)
    out = _REF.sub(lambda m: m.group(4) or m.group(2), out)
    out = _SOURCE.sub(lambda m: m.group(4), out)
    if "{{" in out or "{%" in out:
        snippet = out[out.find("{") : out.find("{") + 60].splitlines()[0]
        raise SqlError("the model uses dbt features fixwitness can't render yet "
                       f"(near '{snippet}'): only ref(), source() and config() are supported. "
                       "Run `dbt compile` and check the compiled SQL instead.")
    return out


def strip_sql(sql: str) -> str:
    sql = sql.strip()
    while sql.endswith(";"):
        sql = sql[:-1].rstrip()
    return sql


def translate(sql: str, dialect: str | None, engine: str, tables: set[str] | None = None) -> str:
    """Translate one statement from a warehouse dialect to the local engine's SQL.

    Names qualified with a database or schema (analytics.raw.orders, `project.dataset.orders`)
    are reduced to the table name when that name is one of the loaded tables or models.
    """
    if not dialect or engine == "warehouse":  # in the warehouse, the SQL runs as written
        return sql
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError as exc:
        raise SqlError("--dialect needs sqlglot (pip install sqlglot)") from exc
    try:
        trees = [t for t in sqlglot.parse(sql, read=dialect) if t is not None]
    except Exception as exc:
        raise SqlError(f"could not parse the query as {dialect} SQL: {exc}") from exc
    if len(trees) != 1:
        raise SqlError(f"expected one SQL statement, found {len(trees)}")
    tree = trees[0]
    known = {t.lower(): t for t in (tables or ())}
    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name in known and name not in ctes:
            table.set("catalog", None)
            table.set("db", None)
            table.set("this", exp.to_identifier(known[name]))
    try:
        return tree.sql(dialect=engine)
    except Exception as exc:
        raise SqlError(f"could not translate the query from {dialect} to {engine} SQL: {exc}") from exc


def prepare(sql: str, dbt: str, dialect: str | None, engine: str, tables: set[str] | None = None) -> str:
    if dbt == "on" or (dbt == "auto" and "{{" in sql):
        sql = render_dbt(sql)
    return translate(strip_sql(sql), dialect, engine, tables)


# ---------------------------------------------------------------- pipelines

_COMMENTS = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRINGS = re.compile(r"'(?:[^']|'')*'")
_FROM_JOIN = re.compile(r"\b(?:from|join)\s+((?:\"[^\"]+\"|[A-Za-z_][\w$]*)(?:\s*\.\s*(?:\"[^\"]+\"|[A-Za-z_][\w$]*))*)",
                        re.IGNORECASE)


def find_models(root: Path) -> dict[str, Path]:
    models: dict[str, Path] = {}
    for p in sorted(root.rglob("*.sql")):
        if p.stem in models:
            raise SqlError(f"two models are named {p.stem}: {models[p.stem]} and {p}")
        models[p.stem] = p
    if not models:
        raise SqlError(f"no .sql models in {root}")
    return models


def dependencies(raw: str, names: set[str], own: str) -> set[str]:
    """Models a model reads: its ref() calls and the tables named after FROM and JOIN."""
    refs = {m.group(4) or m.group(2) for m in _REF.finditer(raw)}
    text = _STRINGS.sub("''", _COMMENTS.sub(" ", _CONFIG.sub("", _REF.sub(" ", raw))))
    tables = set()
    for m in _FROM_JOIN.finditer(text):
        last = re.split(r"\s*\.\s*", m.group(1))[-1].strip('"')
        tables.add(last)
    return (refs | tables) & names - {own}


def run_order(models: dict[str, str]) -> list[str]:
    names = set(models)
    deps = {n: dependencies(sql, names, n) for n, sql in models.items()}
    order, done = [], set()
    while len(order) < len(models):
        ready = sorted(n for n in models if n not in done and deps[n] <= done)
        if not ready:
            stuck = sorted(n for n in models if n not in done)
            raise SqlError("the models depend on each other in a cycle: " + ", ".join(stuck))
        order += ready
        done |= set(ready)
    return order


# ---------------------------------------------------------------- engines

def have_duckdb() -> bool:
    try:
        import duckdb  # noqa: F401
    except ImportError:
        return False
    return True


def choose_engine(engine: str) -> str:
    if engine == "warehouse":
        return engine  # the SQL runs in the warehouse named by FIXWITNESS_WAREHOUSE (see warehouse.py)
    if engine in ("auto", None, ""):
        return "duckdb" if have_duckdb() else "sqlite"
    if engine == "duckdb" and not have_duckdb():
        raise SqlError("engine 'duckdb' was requested but DuckDB is not installed (pip install duckdb)")
    if engine not in ("duckdb", "sqlite"):
        raise SqlError(f"unknown engine {engine!r}; use auto, duckdb or sqlite")
    return engine


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_types(sample: bytes) -> dict[str, str]:
    """Column kinds of one sample table: integer, number, date or text."""
    from fixwitness.cases import parse_sample, _type
    header, data = parse_sample(sample)
    kinds = {}
    for i, col in enumerate(header):
        values = [r[i] for r in data]
        kind = _type(values)
        if kind == "numeric":
            present = [v for v in values if v.strip()]
            kind = "integer" if present and all(_INTEGER.fullmatch(v) for v in present) else "number"
        kinds[col] = kind if kind in ("integer", "number", "date") else "text"
    return kinds


def _column_type(kind: str, engine: str) -> str:
    if kind == "integer":
        return "BIGINT" if engine == "duckdb" else "INTEGER"
    if kind == "number":
        return "DOUBLE" if engine == "duckdb" else "REAL"
    if kind == "date":
        return "DATE" if engine == "duckdb" else "TEXT"
    return "VARCHAR" if engine == "duckdb" else "TEXT"


def _convert(value: str, sql_type: str, table: str, column: str):
    if value == "":
        return None
    if sql_type in ("BIGINT", "INTEGER"):
        if not _INTEGER.fullmatch(value):
            raise SqlError(f"value {value!r} in {table}.{column} is not an integer")
        number = int(value)
        if not -(2 ** 63) <= number < 2 ** 63:
            raise SqlError(f"value {value!r} in {table}.{column} does not fit a 64-bit integer")
        return number
    if sql_type in ("DOUBLE", "REAL"):
        if not _NUMBER.fullmatch(value):
            raise SqlError(f"value {value!r} in {table}.{column} is not a number")
        return float(value)
    if sql_type == "DATE":
        if not _DATE.fullmatch(value):
            raise SqlError(f"value {value!r} in {table}.{column} is not a date (YYYY-MM-DD)")
        try:
            return _dt.date.fromisoformat(value)
        except ValueError as exc:
            raise SqlError(f"value {value!r} in {table}.{column} is not a valid date") from exc
    return value


def typed_rows(name: str, text: str, types: dict[str, dict[str, str]],
               engine: str = "duckdb") -> tuple[list[str], list[str], list[list]]:
    """One table's header, column kinds and rows of typed values (empty cells are None)."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        raise SqlError(f"table {name} has no header row")
    header, data = rows[0], rows[1:]
    if any(c == "" for c in header) or len(set(header)) != len(header):
        raise SqlError(f"table {name} has an empty or repeated column name")
    width = len(header)
    data = [r + [""] * (width - len(r)) if len(r) < width else r for r in data]
    if any(len(r) > width for r in data):
        raise SqlError(f"table {name} has a row with more cells than columns")
    kinds = [types.get(name, {}).get(c, "text") for c in header]  # columns not in the sample: text
    sql_types = [_column_type(k, engine) for k in kinds]
    values = [[_convert(v, t, name, c) for v, t, c in zip(r, sql_types, header)] for r in data]
    return header, kinds, values


def load_tables(con, engine: str, tables: dict[str, str], types: dict[str, dict[str, str]]) -> None:
    for name, text in tables.items():
        header, kinds, values = typed_rows(name, text, types, engine)
        cols = ", ".join(f"{_quote(c)} {_column_type(k, engine)}" for c, k in zip(header, kinds))
        con.execute(f"CREATE TABLE {_quote(name)} ({cols})")
        if values:
            marks = ", ".join(["?"] * len(header))
            con.executemany(f"INSERT INTO {_quote(name)} VALUES ({marks})", values)


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v != v:
            return "NaN"
        return repr(v)
    if isinstance(v, decimal.Decimal):
        return format(v.normalize(), "f") if v == v.to_integral_value() else format(v, "f")
    if isinstance(v, (_dt.date, _dt.datetime, _dt.time)):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).hex()
    return str(v)


def _connect(engine: str):
    if engine == "duckdb":
        import duckdb
        return duckdb.connect(":memory:")
    import sqlite3
    return sqlite3.connect(":memory:")


def _result_csv(cur, ordered: bool) -> bytes:
    header = [d[0] for d in (cur.description or [])]
    rows = [[_cell(v) for v in r] for r in cur.fetchall()]
    if not ordered:
        rows.sort()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def run_query(sql: str, bundle: bytes, engine: str = "auto", dbt: str = "auto", ordered: bool = False,
              dialect: str | None = None) -> bytes:
    """Load the bundle's tables, run the query and return the result as CSV bytes."""
    tables, types = read_bundle(bundle)
    engine = choose_engine(engine)
    sql = prepare(sql, dbt, dialect, engine, set(tables))
    if engine == "warehouse":
        from fixwitness.warehouse import Session, url_from_env
        with Session(url_from_env()) as wh:
            wh.load(tables, types)
            return _result_csv(wh.query(sql), ordered)
    con = _connect(engine)
    try:
        load_tables(con, engine, tables, types)
        return _result_csv(con.execute(sql), ordered)
    finally:
        con.close()


def run_pipeline(root: Path, bundle: bytes, engine: str = "auto", dbt: str = "auto", ordered: bool = False,
                 dialect: str | None = None, outputs: list[str] | None = None) -> bytes:
    """Run every model in a folder in dependency order; return each model's result."""
    tables, types = read_bundle(bundle)
    engine = choose_engine(engine)
    models = {name: p.read_text(encoding="utf-8") for name, p in find_models(root).items()}
    clash = sorted(set(models) & set(tables))
    if clash:
        raise SqlError(f"model(s) {', '.join(clash)} have the same name as an input table")
    wanted = outputs or sorted(models)
    order_file = root / "fixwitness_order.txt"  # written for dbt projects, from dbt's own graph
    if engine == "warehouse":
        from fixwitness.warehouse import Session, ident, url_from_env
        results = {}
        with Session(url_from_env()) as wh:
            wh.load(tables, types)
            names = order_file.read_text(encoding="utf-8").split() if order_file.is_file() else run_order(models)
            for name in names:
                wh.create_as(name, prepare(models[name], dbt, dialect, engine, set(tables) | set(models)))
            for name in wanted:
                if name in models:
                    results[name] = _result_csv(wh.query(f"SELECT * FROM {ident(name, wh.kind)}"), ordered)
        return make_outputs(results)
    con = _connect(engine)
    results: dict[str, bytes] = {}
    try:
        load_tables(con, engine, tables, types)
        names = order_file.read_text(encoding="utf-8").split() if order_file.is_file() else run_order(models)
        for name in names:
            sql = prepare(models[name], dbt, dialect, engine, set(tables) | set(models))
            con.execute(f"CREATE TABLE {_quote(name)} AS {sql}")
        for name in wanted:
            if name in models:
                results[name] = _result_csv(con.execute(f"SELECT * FROM {_quote(name)}"), ordered)
    finally:
        con.close()
    return make_outputs(results)  # a wanted model this side does not have is left out, and reported


# ---------------------------------------------------------------- cases

def _repeats_a_key(content: bytes, column: str | None, value: str | None) -> bool:
    """True when the case's value also appears in another row of the same column."""
    if not column or value is None:
        return False
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"), newline="")))
    if not rows or column not in rows[0]:
        return False
    i = rows[0].index(column)
    cells = [r[i] for r in rows[1:] if i < len(r)]
    return cells.count(value) > 1

# Categories that test how a program parses CSV text. In SQL mode fixwitness loads the tables
# itself, so these would only repeat other cases.
SQL_SKIP_CATEGORIES = {"header-names"}
SQL_SKIP_VALUES = ("<CRLF line endings>",)


def generate_sql_cases(tables: dict[str, bytes], types: dict[str, dict[str, str]],
                       columns: list[str] | None = None, rows: int = 3, max_cases: int = 300,
                       seed: int = 1337, review: list[str] | None = None,
                       incident_tables: dict[str, bytes] | None = None, focus: list[str] | None = None):
    """Cases for a query over several tables: vary one table at a time, keep the others as sampled.

    `columns` may name columns as "table.column" (or just "column" when only one table has it).
    When there are more cases than max_cases, one case of every (column, category) pair is kept
    first, so each kind of input reaches each column; the rest is a seeded random sample.
    """
    import random
    from fixwitness.cases import Case, generate_cases, parse_sample, UNQUOTED, IN_NOTE_UNQUOTED

    wanted: dict[str, list[str]] = {}
    for spec in columns or []:
        if "." in spec and spec.split(".", 1)[0] in tables:
            t, c = spec.split(".", 1)
            wanted.setdefault(t, []).append(c)
            continue
        owners = [t for t, data in tables.items() if spec in types.get(t, {})]
        if not owners:
            raise ValueError(f"column {spec!r} is not in any table ({', '.join(tables)})")
        if len(owners) > 1:
            raise ValueError(f"column {spec!r} is in several tables ({', '.join(owners)}); write it as table.column")
        wanted.setdefault(owners[0], []).append(spec)
    def loadable(t: str, data: bytes) -> bool:
        """Could a warehouse load this table with the sample's column types? (No: skip the case.)"""
        try:
            rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
            header = rows[0]
            for r in rows[1:]:
                for col, v in zip(header, r):
                    _convert(v, _column_type(types.get(t, {}).get(col, "text"), "duckdb"), t, col)
        except (SqlError, UnicodeDecodeError, csv.Error, IndexError):
            return False
        return True

    names = [t for t in tables if not columns or t in wanted]
    cases = []
    own_values = set()  # cases made from the sample's own value (PAID for paid): kept first under the cap
    for t in names:
        sub = generate_cases(tables[t], wanted.get(t), rows, 5000, seed, review, None, False,
                             (incident_tables or {}).get(t))
        for c in sub:
            if c.category in SQL_SKIP_CATEGORIES or c.value in SQL_SKIP_VALUES:
                continue
            if c.value and (c.value.endswith(UNQUOTED) or c.value.endswith(IN_NOTE_UNQUOTED)):
                continue  # the same table once loaded
            if not loadable(t, c.content):
                continue  # e.g. "1,250" in a numeric column: the table could not hold it
            kind = c.kind
            if kind == "valid" and "duplicate" in (review or []) and _repeats_a_key(c.content, c.column, c.value):
                kind = "review"  # the value equals another row's: a duplicate key, which is under review
            bundle = make_bundle({**tables, t: c.content}, types)
            cases.append(Case(id=f"{len(cases):03d}", category=c.category, kind=kind,
                              column=f"{t}.{c.column}" if c.column else t,
                              value=c.value, content=bundle))
        # SQL-specific: a column that is entirely NULL (aggregates and COALESCE differ), and a whole
        # row repeated (DISTINCT, UNION and join fan-out differ).
        header, data = parse_sample(tables[t])
        base = data[:rows]
        extra = []
        for col in wanted.get(t) or header:
            i = header.index(col)
            extra.append(("null-column", f"{t}.{col}", "<all NULL>", [r[:i] + [""] + r[i + 1:] for r in base]))
        extra.append(("duplicate-row", t, "<first row repeated>", [base[0]] + base))
        # The row's own text in another case or with padding: SQL comparisons are exact, so a
        # LOWER(), UPPER() or TRIM() added to a filter or join changes which rows match.
        target = min(1, len(base) - 1)
        for col in wanted.get(t) or header:
            if types.get(t, {}).get(col) != "text":
                continue
            i = header.index(col)
            v = base[target][i]
            variants = [("case", x) for x in dict.fromkeys((v.upper(), v.lower(), v.title()))] + \
                       [("whitespace", " " + v), ("whitespace", v + " ")]
            for category, x in variants:
                if x == v or not v.strip():
                    continue
                body = [list(r) for r in base]
                body[target][i] = x
                extra.append((category, f"{t}.{col}", x, body))
        for category, column, value, body in extra:
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(header)
            w.writerows(body)
            content = buf.getvalue().encode("utf-8")
            if not loadable(t, content):
                continue
            kind = "review" if category in (review or []) else "valid"
            if category in ("case", "whitespace"):
                own_values.add(len(cases))
            cases.append(Case(id=f"{len(cases):03d}", category=category, kind=kind, column=column, value=value,
                              content=make_bundle({**tables, t: content}, types)))
    if len(cases) > max_cases:
        focused = set(focus or [])
        seen, first, near, rest = set(), [], [], []
        for i in sorted(range(len(cases)), key=lambda i: (i not in own_values, i)):
            c = cases[i]
            key = (c.column, c.category)
            if key not in seen:
                first.append(i)
            elif c.column in focused:
                near.append(i)  # the columns the change touched keep all their cases
            else:
                rest.append(i)
            seen.add(key)
        chosen = set(first[:max_cases])
        chosen |= set(near[: max(0, max_cases - len(chosen))])
        budget = max_cases - len(chosen)
        rest.sort()
        chosen |= set(random.Random(seed).sample(rest, min(max(0, budget), len(rest))))
        cases = [c for i, c in enumerate(cases) if i in chosen]
    for i, c in enumerate(cases):
        c.id = f"{i:03d}"
    return cases
