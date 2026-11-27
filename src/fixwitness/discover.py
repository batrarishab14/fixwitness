"""Finding what a check needs without being told: the tables a query or a function reads, the
data files that hold them, and the functions a change touched.

Everything found is written into the plan's notes, so the user sees what was assumed.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import re
from pathlib import Path

DATA_SUFFIXES = (".csv", ".parquet", ".jsonl", ".ndjson")
DATA_DIRS = ["", "data", "seeds", "sample", "samples", "fixtures", "testdata", "test_data", "tests/data",
             "tests/fixtures", "data/samples", "data/sample"]
SKIP_PARTS = {".git", ".fixwitness", "node_modules", ".venv", "venv", "target", "dbt_packages", "__pycache__",
              "fixwitness-report"}

_COMMENTS = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)
_STRINGS = re.compile(r"'(?:[^']|'')*'")
_NAME = r"(?:\"[^\"]+\"|`[^`]+`|\[[^\]]+\]|[A-Za-z_][\w$]*)"
_TABLE = re.compile(rf"\b(?:from|join)\s+({_NAME}(?:\s*\.\s*{_NAME})*)", re.IGNORECASE)
_CTE = re.compile(rf"(?:\bwith(?:\s+recursive)?|,)\s*({_NAME})\s*(?:\([^)]*\)\s*)?as\s*(?:not\s+)?(?:materialized\s*)?\(",
                  re.IGNORECASE)
_REF = re.compile(r"\{\{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*['\"]([^'\"]+)['\"]\s*)?\)\s*\}\}")
_SOURCE = re.compile(r"\{\{\s*source\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")
_FUNCS = {"unnest", "generate_series", "range", "read_csv", "read_parquet", "read_json", "lateral", "table",
          "values", "select"}


def _bare(name: str) -> str:
    return name.strip('"`[]')


def query_tables(sql: str) -> list[str]:
    """The tables a query reads (names after FROM and JOIN, without CTEs), last part of qualified names."""
    refs = [m.group(2) or m.group(1) for m in _REF.finditer(sql)] + [m.group(1) for m in _SOURCE.finditer(sql)]
    text = _REF.sub(lambda m: m.group(2) or m.group(1), sql)
    text = _SOURCE.sub(lambda m: m.group(1), text)
    text = _STRINGS.sub("''", _COMMENTS.sub(" ", text))
    text = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", text, flags=re.DOTALL)
    ctes = {_bare(m.group(1)).lower() for m in _CTE.finditer(text)}
    found = []
    for m in _TABLE.finditer(text):
        name = _bare(re.split(r"\s*\.\s*", m.group(1))[-1])
        after = text[m.end():m.end() + 2].lstrip()
        if name.lower() in ctes or name.lower() in _FUNCS or after.startswith("("):
            continue
        found.append(name)
    return list(dict.fromkeys(refs + found))


# ---------------------------------------------------------------- data files

def data_index(roots: list[Path]) -> dict[str, Path]:
    """Data files by lower-case stem, searched in the usual data folders under each root (first match wins)."""
    index: dict[str, Path] = {}
    for root in roots:
        for sub in DATA_DIRS:
            d = root / sub if sub else root
            if not d.is_dir():
                continue
            for suffix in DATA_SUFFIXES:
                for p in sorted(d.glob(f"*{suffix}")):
                    if p.is_file() and not (SKIP_PARTS & set(p.parts)):
                        index.setdefault(p.stem.lower(), p)
    return index


def match_tables(names: list[str], roots: list[Path]) -> tuple[dict[str, Path], list[str]]:
    """(table -> data file, tables with no file). A table matches a file of the same name, or raw_<name>."""
    index = data_index(roots)
    found, missing = {}, []
    for name in names:
        key = name.lower()
        p = index.get(key) or index.get(f"raw_{key}") or index.get(key.removeprefix("raw_"))
        if p is None:
            missing.append(name)
        else:
            found[name] = p
    return found, missing


def table_bytes(path: Path) -> bytes:
    """A data file as CSV bytes: CSV as it is, Parquet through pyarrow, JSON Lines of flat records."""
    suffix = path.suffix.lower()
    data = path.read_bytes()
    if suffix == ".parquet":
        from fixwitness.formats import parquet_to_csv
        return parquet_to_csv(data)
    if suffix in (".jsonl", ".ndjson"):
        records = [json.loads(line) for line in data.decode("utf-8-sig").splitlines() if line.strip()]
        if not records or not all(isinstance(r, dict) for r in records):
            raise ValueError(f"{path.name}: a table in JSON Lines needs one JSON object per line")
        header = list(dict.fromkeys(k for r in records for k in r))
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        for r in records:
            w.writerow(["" if r.get(k) is None else json.dumps(r[k]) if isinstance(r.get(k), (dict, list))
                        else str(r[k]).lower() if isinstance(r.get(k), bool) else str(r[k]) for k in header])
        return buf.getvalue().encode("utf-8")
    return data


# ---------------------------------------------------------------- Python functions

def _functions(source: str) -> dict[str, ast.FunctionDef]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}


def required_params(fn: ast.FunctionDef) -> list[str]:
    args = fn.args.posonlyargs + fn.args.args
    n_default = len(fn.args.defaults)
    required = [a.arg for a in args[: len(args) - n_default]]
    required += [a.arg for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if d is None]
    return [a for a in required if a not in ("self", "cls")]


def changed_functions(before: str, after: str) -> list[str]:
    """Top-level public functions present in both versions whose code differs (or whose helpers do)."""
    b, a = _functions(before), _functions(after)
    changed = []
    module_changed = _module_rest(before) != _module_rest(after)
    for name in b:
        if name not in a:
            continue
        if ast.dump(b[name]) != ast.dump(a[name]) or module_changed:
            changed.append(name)
    return changed


def _module_rest(source: str) -> str:
    """Everything at module level except public functions: helpers, imports, constants."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    rest = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and not n.name.startswith("_"))]
    return ast.dump(ast.Module(body=rest, type_ignores=[]))


def frame_functions(before: str, after: str, roots: list[Path]) -> list[tuple[str, dict[str, Path]]]:
    """Changed functions whose every required parameter matches a data file: (name, table -> file)."""
    if not re.search(r"^\s*(?:import|from)\s+(?:pandas|polars|pyspark)\b", before + "\n" + after, re.M):
        return []
    out = []
    fns = _functions(after)
    for name in changed_functions(before, after):
        params = required_params(fns[name])
        if not params:
            continue
        found, missing = match_tables(params, roots)
        if not missing:
            out.append((name, found))
    return out


def is_runnable_script(source: str) -> bool:
    """Code at module level that does work (reads argv/stdin or calls something), not only definitions."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant):
            continue  # a docstring
        if isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets):
            continue  # a constant
        return True
    return False
