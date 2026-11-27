"""Shrink a difference to the smallest input that still shows it.

A case is a whole sample with one value changed. To make a finding easy to check, fixwitness
removes rows (every table's rows in SQL and DataFrame mode, data lines of a CSV file, records of
a JSON Lines file) as long as the original and the fix still differ in the same way, the way
delta debugging does. Rows holding the changed value are kept, so the sentence that explains the
finding stays true. The verdict does not depend on this: it only changes the input shown in the
report and saved in the reproduction.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import time

MAX_TESTS = 30


def _ddmin(units: list, test, budget: list[int]) -> list:
    n = 2
    while len(units) >= 1 and budget[0] > 0:
        size = max(1, -(-len(units) // n))
        reduced = False
        for i in range(0, len(units), size):
            if budget[0] <= 0:
                break
            cand = units[:i] + units[i + size:]
            budget[0] -= 1
            if test(cand):
                units, reduced = cand, True
                n = max(2, n - 1)
                break
        if not reduced:
            if size == 1:
                break
            n = min(len(units), n * 2)
    return units


def _protect(header: list[str], rows: list[list[str]], case, column: str | None) -> set[int]:
    """Rows that carry the change itself."""
    keep = set()
    if case.category == "duplicate-row":
        seen: dict[tuple, int] = {}
        for i, r in enumerate(rows):
            t = tuple(r)
            if t in seen:
                keep |= {seen[t], i}
            seen.setdefault(t, i)
        return keep
    if column in header and case.category not in ("null-column",):
        ci = header.index(column)
        for i, r in enumerate(rows):
            if ci < len(r) and r[ci] == (case.value or ""):
                keep.add(i)
    return keep


def _csv_text(header, rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def plan_units(case, input_fmt: str, tables: bool):
    """(removable units, rebuild(units) -> bytes) or None when this input can't be shrunk safely."""
    if case.category in ("file-structure", "header-names", "delimiter-mix", "csv-structure", "attack"):
        return None
    if tables:
        from fixwitness.sql import make_bundle, read_bundle
        all_tables, types = read_bundle(case.content)
        parsed = {n: list(csv.reader(io.StringIO(t, newline=""))) for n, t in all_tables.items()}
        varied, col = (case.column.split(".", 1) + [None])[:2] if case.column and "." in case.column \
            else (case.column, None)
        fixed, units = [], []
        for name, rows in parsed.items():
            if not rows:
                continue
            header, data = rows[0], rows[1:]
            protect = _protect(header, data, case, col) if name == varied else set()
            for i in range(len(data)):
                (fixed if i in protect else units).append((name, i))
        if not units:
            return None

        def rebuild(kept: list) -> bytes:
            chosen = set(kept) | set(fixed)
            out = {}
            for name, rows in parsed.items():
                if not rows:
                    out[name] = all_tables[name].encode("utf-8")
                    continue
                out[name] = _csv_text(rows[0], [r for i, r in enumerate(rows[1:]) if (name, i) in chosen]).encode("utf-8")
            if varied in parsed and len(parsed[varied]) > 1 and not any(n == varied for n, _ in chosen):
                return b""  # keep at least one row of the table the case is about
            return make_bundle(out, types)
        return units, rebuild
    text = case.content.decode("utf-8", "replace")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    trailing = lines[-1] == ""
    if trailing:
        lines = lines[:-1]
    if input_fmt == "json":
        if not lines or not text.lstrip().startswith("{") or len(lines) < 2:
            return None  # one JSON document, not JSON Lines
        header, data = None, lines
    else:
        parsed = list(csv.reader(io.StringIO(text, newline="")))
        if len(parsed) != len(lines) or len(lines) < 2:
            return None  # a quoted field spans lines: removing lines could break a record
        header, data = lines[0], lines[1:]
    col = case.column
    protect = set()
    for i, line in enumerate(data):
        if case.value and case.value in line and case.category not in ("null-column",):
            protect.add(i)
    if case.category == "duplicate-row":
        seen = {}
        for i, line in enumerate(data):
            if line in seen:
                protect |= {seen[line], i}
            seen.setdefault(line, i)
    units = [i for i in range(len(data)) if i not in protect]
    if not units or col is None and case.category != "duplicate-row" and not protect:
        return None

    def rebuild(kept: list) -> bytes:
        chosen = sorted(set(kept) | protect)
        if not chosen:
            return b""
        body = ([header] if header is not None else []) + [data[i] for i in chosen]
        return (nl.join(body) + (nl if trailing else "")).encode("utf-8")
    return units, rebuild


def shrink_case(case, status: str, run_pair, compare_fn, input_fmt: str, tables: bool,
                deadline: float) -> tuple[object, object, object] | None:
    """(smaller case, original's result, fix's result), or None when nothing could be removed."""
    planned = plan_units(case, input_fmt, tables)
    if planned is None:
        return None
    units, rebuild = planned
    best: dict = {}

    def test(kept: list) -> bool:
        if time.time() > deadline:
            return False
        content = rebuild(kept)
        if not content:
            return False
        b, a = run_pair(content)
        if not b.ok or b.output is None:
            return False
        if status == "after-failed":
            ok = not a.ok or a.output is None
        else:
            ok = a.ok and a.output is not None and compare_fn(b.output, a.output) == "changed"
        if ok:
            best.update(content=content, before=b, after=a)
        return ok

    budget = [MAX_TESTS]
    _ddmin(units, test, budget)
    if not best:
        return None
    return dataclasses.replace(case, content=best["content"]), best["before"], best["after"]
