"""Each difference in plain English, with the tables that show it.

For every difference fixwitness keeps (the input, the original's output, the fix's output), this
module builds:
- a sentence anyone can read: "If an `orders` row has an empty `amount`, `orders` for `east`
  changes from 2 to 1.";
- an impact label for the decision makers: the job fails, rows are added or lost, numbers change,
  or values change;
- the input table with the changed cells marked, and both outputs aligned row by row with the
  differing cells marked, for the people who check the evidence.
"""

from __future__ import annotations

import csv
import io
import json
import math

MAX_ROWS = 12
IMPACTS = {
    "fails": "The job fails",
    "rows": "Rows added or lost",
    "numbers": "Numbers change",
    "values": "Values change",
}


# ---------------------------------------------------------------- tables from bytes

def _csv_table(data: bytes) -> tuple[list[str], list[list[str]]] | None:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _records_table(records: list) -> tuple[list[str], list[list[str]]]:
    header: list[str] = []
    for r in records:
        for k in (r.keys() if isinstance(r, dict) else ["value"]):
            if k not in header:
                header.append(k)
    rows = []
    for r in records:
        if isinstance(r, dict):
            rows.append([_cell(r[k]) if k in r else "<missing>" for k in header])
        else:
            rows.append([_cell(r)])
    return header, rows


def table_of(data: bytes | None, fmt: str) -> tuple[list[str], list[list[str]]] | None:
    """(header, rows) for an input or output, by its format: csv, json, parquet or text."""
    if data is None:
        return None
    from fixwitness.formats import is_parquet, parquet_to_csv, parse_json_output
    if is_parquet(data):
        try:
            data = parquet_to_csv(data)
        except Exception:
            return None
        fmt = "csv"
    if fmt == "json":
        value = parse_json_output(data)
        if value is None and not data.strip():
            return [], []
        if value is not None:
            if isinstance(value, dict):  # an API-style wrapper holds the records; else one record
                lists = [v for v in value.values() if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)]
                value = lists[0] if len(lists) == 1 else [value]
            if isinstance(value, list):
                return _records_table(value)
            return ["value"], [[_cell(value)]]
    if fmt in ("csv", "json"):
        return _csv_table(data)
    text = data.decode("utf-8", "replace")
    return ["line"], [[ln] for ln in text.splitlines()]


# ---------------------------------------------------------------- aligning two outputs

def _num(s: str) -> float | None:
    try:
        f = float(s)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _same(a: str, b: str, tol: float) -> bool:
    if a == b:
        return True
    x, y = _num(a), _num(b)
    return x is not None and y is not None and (x == y or (tol and abs(x - y) <= tol * max(1.0, abs(x), abs(y))))


def align(before, after, tol: float = 1e-9) -> dict:
    """Rows of both outputs side by side: matched by the first column when it is a key in both,
    else by position."""
    hb, rb = before
    ha, ra = after
    cols = list(hb) + [c for c in ha if c not in hb]
    ib = {c: i for i, c in enumerate(hb)}
    ia = {c: i for i, c in enumerate(ha)}

    def get(row, idx, c):
        i = idx.get(c)
        return row[i] if i is not None and i < len(row) else None

    keyed = bool(hb and ha and hb[0] == ha[0]) and len({r[0] for r in rb if r}) == len(rb) \
        and len({r[0] for r in ra if r}) == len(ra)
    pairs = []
    if keyed:
        amap = {r[0]: r for r in ra if r}
        seen = set()
        for r in rb:
            pairs.append((r, amap.get(r[0])))
            seen.add(r[0])
        pairs += [(None, r) for r in ra if r and r[0] not in seen]
    else:
        for i in range(max(len(rb), len(ra))):
            pairs.append((rb[i] if i < len(rb) else None, ra[i] if i < len(ra) else None))
    lines = []
    for b, a in pairs:
        cells = []
        for c in cols:
            vb = get(b, ib, c) if b is not None else None
            va = get(a, ia, c) if a is not None else None
            cells.append({"before": vb, "after": va,
                          "changed": b is not None and a is not None and not _same(vb or "", va or "", tol)
                          and not (vb is None and va is None)})
        lines.append({"state": "both" if b is not None and a is not None else ("original" if b is not None else "fix"),
                      "cells": cells})
    return {"columns": cols, "key": cols[0] if keyed and cols else None, "rows": lines,
            "columns_only_original": [c for c in hb if c not in ia], "columns_only_fix": [c for c in ha if c not in ib]}


# ---------------------------------------------------------------- the sentence

def _q(v, limit: int = 40) -> str:
    s = str(v)
    s = s if len(s) <= limit else s[: limit - 1] + "…"
    return s if _num(s) is not None and s.strip() == s else f"'{s}'"


def _a(word: str) -> str:
    return "an" if word.lstrip("`'").lower()[:1] in "aeiou" else "a"


def _where(column: str | None) -> tuple[str | None, str | None]:
    """(table, column) from a case column such as 'orders.amount', 'amount' or 'orders'."""
    if not column:
        return None, None
    if "." in column and not column.endswith("]"):
        t, c = column.split(".", 1)
        return t, c
    return None, column


def input_phrase(category: str, column: str | None, value, tables: bool) -> str:
    table, col = _where(column)
    if tables and col and table is None:  # a table-level case (column is the table)
        table, col = col, None
    row = f"{_a(table)} `{table}` row" if table else "a row"
    c = f"`{col}`" if col else "a value"
    v = _q(value) if value is not None else ""
    if category == "attack":
        return f"{c} holds an attack payload"
    if category == "empty":
        return f"{row} has an empty {c}"
    if category in ("null-column",):
        return f"every {c} in `{table}` is empty (NULL)" if table else f"every {c} is empty"
    if category == "null":
        return f"{c} is null"
    if category == "missing-key":
        return f"a record has no {c} key"
    if category == "duplicate-row":
        return f"{_a(table)} `{table}` row appears twice" if table else "a row appears twice"
    if category == "duplicate":
        return f"{c} repeats the value of another row ({v})"
    if category == "case":
        return f"{c} is written in another case ({v})"
    if category == "whitespace":
        return f"{c} has extra spaces ({v})"
    if category == "numeric-format":
        return f"{c} is the number {v}"
    if category == "date-format":
        return f"{c} is the date {v}"
    if category == "json-type":
        return f"{c} has another JSON type ({v})"
    if category == "json-escape":
        return f"{c} holds escaped characters ({v})"
    if category == "array":
        return f"the array {c} is {'empty' if value in ('[]', '<empty>') else 'longer'} ({v})"
    if category == "schema":
        return f"the input has another column layout ({value})" if value else "the input has another column layout"
    if category == "header-names":
        return f"a column name holds unusual characters ({v})"
    if category == "file-structure":
        return f"the file is {str(value).strip('<>')}" if value else "the file has another structure"
    if category in ("unicode", "long", "punctuation", "quotes", "shell-metachar", "csv-structure", "delimiter-mix"):
        return f"{c} is {v}"
    return f"{c} is {v}" if value is not None else f"the input is changed ({category})"


def _effect(view: dict, model: str | None) -> tuple[str, str]:
    """(impact, phrase) from an aligned pair of outputs."""
    rows = view["rows"]
    only_b = [r for r in rows if r["state"] == "original"]
    only_a = [r for r in rows if r["state"] == "fix"]
    changed = [(r, i) for r in rows if r["state"] == "both" for i, c in enumerate(r["cells"]) if c["changed"]]
    where = f"in `{model}`, " if model else ""
    if view["columns_only_original"] or view["columns_only_fix"]:
        gone, new = view["columns_only_original"], view["columns_only_fix"]
        bits = ([f"column{'s' if len(gone) > 1 else ''} {', '.join(f'`{c}`' for c in gone)} disappear"
                 f"{'' if len(gone) > 1 else 's'}"] if gone else []) + \
               ([f"column{'s' if len(new) > 1 else ''} {', '.join(f'`{c}`' for c in new)} appear"
                 f"{'' if len(new) > 1 else 's'}"] if new else [])
        return "values", where + " and ".join(bits)
    if only_b or only_a:
        nb = sum(1 for r in rows if r["state"] in ("both", "original"))
        na = sum(1 for r in rows if r["state"] in ("both", "fix"))
        extra = ""
        sample = (only_a or only_b)[0]
        key = next((c["after"] if c["after"] is not None else c["before"] for c in sample["cells"]), None)
        if key not in (None, ""):
            extra = f"; {'a new row' if only_a else 'the row'} for {_q(key)} {'appears' if only_a else 'is missing'}"
        return "rows", f"{where}the output has {na} row{'s' if na != 1 else ''} instead of {nb}{extra}"
    if changed:
        r, i = changed[0]
        col = view["columns"][i]
        cell = r["cells"][i]
        key = r["cells"][0]["before"] if view["key"] and i != 0 else None
        for_key = f" for {_q(key)}" if key not in (None, "") else ""
        b, a = cell["before"], cell["after"]
        show = lambda s: "empty" if s in (None, "") else _q(s)  # noqa: E731
        more = len(changed) - 1
        impact = "numbers" if (_num(b or "") is not None or _num(a or "") is not None) else "values"
        return impact, (f"{where}`{col}`{for_key} changes from {show(b)} to {show(a)}"
                        + (f" (and {more} more cell{'s' if more != 1 else ''})" if more else ""))
    return "values", f"{where}the output changes"


def _first_line(text: str | None) -> str:
    if not text:
        return "no output"
    lines = [ln.strip() for ln in str(text).strip().splitlines() if ln.strip()]
    for ln in reversed(lines):  # the exception line of a traceback
        if "Error" in ln or "Exception" in ln or ln.startswith("fixwitness."):
            return ln[:160]
    return lines[-1][:160] if lines else "no output"


def explain_case(case, before, after, output_mode: str, input_fmt: str, tables: bool, tol: float) -> dict:
    """The plain-English sentence, the impact and the evidence tables for one difference."""
    from fixwitness.sql import read_bundle, read_outputs
    result: dict = {"impact": None, "sentence": None, "input": None, "outputs": None, "error": None, "model": None}
    # the input that shows it
    table_name, col = _where(case.column)
    if tables:
        try:
            all_tables, _ = read_bundle(case.content)
        except Exception:
            all_tables = {}
        if table_name is None and case.column in all_tables:
            table_name, col = case.column, None
        if table_name is None and all_tables:
            table_name = next(iter(all_tables))
        t = _csv_table(all_tables.get(table_name, "").encode("utf-8")) if table_name in all_tables else None
        others = {n: _csv_table(x.encode("utf-8")) for n, x in all_tables.items() if n != table_name}
    else:
        t = table_of(case.content, "json" if input_fmt == "json" else "csv")
        others = {}
        if t is not None and col and "." in col:
            col = col.split(".", 1)[0].split("[", 1)[0]
    if t is not None:
        header, rows = t
        if case.category == "missing-key" and col and col not in header and rows:
            header = header + [col]  # show the key that is left out
            rows = [r + ["<missing>"] for r in rows]
        marks = []
        if col in header:
            ci = header.index(col)
            for ri, r in enumerate(rows[:MAX_ROWS]):
                v = r[ci] if ci < len(r) else ""
                if case.category in ("null-column",) or v == (case.value or "") or (
                        case.category in ("empty", "null") and v in ("", "null")) or (
                        case.category == "missing-key" and v == "<missing>"):
                    marks.append([ri, ci])
        result["input"] = {"name": table_name, "header": header, "rows": rows[:MAX_ROWS], "marks": marks,
                           "more_rows": max(0, len(rows) - MAX_ROWS),
                           "other_tables": {n: {"header": h, "rows": r[:MAX_ROWS]} for n, (h, r) in
                                            ((n, x) for n, x in others.items() if x is not None)}}
    phrase = input_phrase(case.category, case.column, case.value, tables)
    if not after.ok or after.output is None:
        err = after.error or ("timed out" if after.timed_out else
                              (after.stderr.decode("utf-8", "replace") if isinstance(after.stderr, bytes)
                               else after.stderr))
        result["error"] = _first_line(err)
        result["impact"] = "fails"
        result["sentence"] = f"If {phrase}, the fix fails ({result['error']}) while the original runs."
        ob = table_of(before.output, output_mode)
        if ob is not None:
            result["original_output"] = {"header": ob[0], "rows": ob[1][:MAX_ROWS], "marks": [],
                                         "more_rows": max(0, len(ob[1]) - MAX_ROWS)}
        return result
    b_out, a_out = before.output, after.output
    named_b, named_a = read_outputs(b_out), read_outputs(a_out)
    if named_b is not None and named_a is not None:
        for name in sorted(set(named_b) | set(named_a)):
            if named_b.get(name) != named_a.get(name):
                result["model"] = name
                if name not in named_a:
                    result["impact"] = "rows"
                    result["sentence"] = f"If {phrase}, the fix no longer produces `{name}`."
                    return result
                if name not in named_b:
                    result["impact"] = "values"
                    result["sentence"] = f"If {phrase}, the fix produces a new output `{name}`."
                    return result
                b_out, a_out = named_b[name], named_a[name]
                break
    tb, ta = table_of(b_out, output_mode), table_of(a_out, output_mode)
    if tb is None or ta is None:
        result["impact"] = "values"
        result["sentence"] = f"If {phrase}, the output changes."
        return result
    view = align(tb, ta, tol)
    impact, effect = _effect(view, result["model"])
    result["impact"], result["outputs"] = impact, view
    result["sentence"] = f"If {phrase}, {effect}."
    return result


def decision(verdict: str, n_changed: int, n_checks: int, n_failed: int) -> tuple[str, str]:
    """(headline, tone) for the top of a report."""
    if verdict == "PASS":
        return ("Safe to merge: every change gives the same results on every input checked."
                if n_checks > 1 else "Safe to merge: the change gives the same results on every input checked."), "pass"
    if verdict == "FAIL":
        if n_checks > 1:
            return (f"Don't merge yet: {n_failed} of {n_checks} changes alter results.", "fail")
        return ("Don't merge yet: the change alters results on inputs your data can contain.", "fail")
    return ("Needs a look: fixwitness could not compare enough inputs to decide.", "review")
