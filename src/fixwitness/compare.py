"""Compare what the original and the fix produced for the same input."""

from __future__ import annotations

import csv
import decimal
import difflib
import io
import re
from dataclasses import dataclass, field, replace

from fixwitness.sql import read_outputs

MAX_CELL_DIFFS = 5
MAX_TEXT_LINES = 12
MASK = "<masked>"


@dataclass
class CompareOptions:
    mode: str = "csv"                       # "csv" or "text"
    ignore_columns: set[str] = field(default_factory=set)
    ignore_patterns: list[re.Pattern] = field(default_factory=list)
    tolerance: float = 0.0                  # relative tolerance for numeric cells
    unordered: bool = False                 # compare rows (or lines) as a multiset
    columns_by_name: bool = False           # SQL results: columns are matched by name, not position
    numeric_forms: bool = False             # opt in: "1" and "1.0", "1e+30" and "1e30" are the same number
                                            # (default: an integer turning into a decimal is a change)


def _short(value: str, limit: int = 80) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def parse_rows(data: bytes) -> list[list[str]] | None:
    try:
        return list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
    except (UnicodeDecodeError, csv.Error):
        return None


def _mask(value: str, patterns: list[re.Pattern]) -> str:
    for p in patterns:
        value = p.sub(MASK, value)
    return value


_PLAIN_NUMBER = re.compile(r"-?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?")


def _same_number(a: str, b: str) -> bool:
    """The same number written differently ("1" / "1.0", "1e+30" / "1e30", "-0.0" / "0.0"). Exact decimal
    equality, so a lost digit still differs; text such as "007" (a code, not a number) is left alone."""
    if not (_PLAIN_NUMBER.fullmatch(a) and _PLAIN_NUMBER.fullmatch(b)):
        return False
    if re.match(r"-?0[0-9]", a) or re.match(r"-?0[0-9]", b):
        return False
    try:
        return decimal.Decimal(a) == decimal.Decimal(b)
    except decimal.InvalidOperation:
        return False


def _both_zero(a: str, b: str) -> bool:
    """"-0.0" and "0.0" (the sign of a zero) are the same number: not a difference in the data."""
    try:
        return float(a) == 0.0 and float(b) == 0.0
    except ValueError:
        return False


def _num_equal(a: str, b: str, tol: float) -> bool:
    try:
        x, y = float(a), float(b)
    except ValueError:
        return False
    return abs(x - y) <= tol * max(1.0, abs(x), abs(y))


def _normalise_csv(rows: list[list[str]], opts: CompareOptions) -> tuple[list[str], list[list[str]]]:
    header = rows[0] if rows else []
    keep = [i for i, name in enumerate(header) if name not in opts.ignore_columns]
    width = max((len(r) for r in rows), default=0)
    keep += [i for i in range(len(header), width)]  # unnamed extra cells are kept
    out = []
    for r in rows[1:]:
        out.append([_mask(r[i], opts.ignore_patterns) if i < len(r) else "<missing>" for i in keep])
    if opts.unordered:
        out.sort()
    return [header[i] if i < len(header) else f"col{i}" for i in keep], out


def output_headers(data: bytes | None) -> dict[str, list[str]] | None:
    """The column names of each output ({"": header} for a single CSV), or None if not CSV."""
    if data is None:
        return None
    named = read_outputs(data)
    if named is not None:
        heads = {}
        for name, part in named.items():
            rows = parse_rows(part)
            heads[name] = rows[0] if rows else []
        return heads
    rows = parse_rows(data)
    return None if rows is None else {"": rows[0] if rows else []}


def _named_options(opts: CompareOptions, name: str) -> CompareOptions:
    cols = {c.split(".", 1)[1] for c in opts.ignore_columns if c.startswith(name + ".")}
    cols |= {c for c in opts.ignore_columns if "." not in c}
    return replace(opts, ignore_columns=cols)


def _compare_named(before: dict[str, bytes], after: dict[str, bytes], opts: CompareOptions) -> tuple[str, list[str]]:
    """Several named outputs (a pipeline): compare each and say which one differs."""
    details: list[str] = []
    statuses = []
    for name in sorted(set(before) | set(after)):
        if name not in after:
            statuses.append("changed")
            details.append(f"{name}: only in the original's output")
            continue
        if name not in before:
            statuses.append("changed")
            details.append(f"{name}: only in the fix's output")
            continue
        st, det = compare(before[name], after[name], _named_options(opts, name))
        statuses.append(st)
        if st == "changed":
            details += [f"{name}: {d}" for d in det]
    if "changed" in statuses:
        return "changed", details[: MAX_CELL_DIFFS * 2]
    if all(st == "identical" for st in statuses):
        return "identical", []
    return "same-data", ["every compared cell of every output is equal"]


def _parquet_as_csv(data: bytes) -> bytes:
    from fixwitness.formats import is_parquet, parquet_to_csv
    if is_parquet(data):
        try:
            return parquet_to_csv(data)
        except Exception:  # unreadable or pyarrow missing: compare the bytes
            return data
    return data


def compare(before: bytes, after: bytes, opts: CompareOptions) -> tuple[str, list[str]]:
    """Return (status, details). Status is 'identical', 'same-data' or 'changed'."""
    if before == after:
        return "identical", []
    named_b, named_a = read_outputs(before), read_outputs(after)
    if named_b is not None and named_a is not None:
        return _compare_named(named_b, named_a, opts)
    before, after = _parquet_as_csv(before), _parquet_as_csv(after)
    if before == after:
        return "same-data", ["the Parquet files hold the same values"]
    if opts.mode == "json":
        from fixwitness.formats import compare_json
        result = compare_json(before, after, opts)
        if result is not None:
            return result
    if opts.mode in ("csv", "json"):
        b_rows, a_rows = parse_rows(before), parse_rows(after)
        if b_rows is not None and a_rows is not None:
            reordered = False
            if b_rows[:1] != a_rows[:1]:
                hb0, ha0 = (b_rows[0] if b_rows else []), (a_rows[0] if a_rows else [])
                if not (opts.columns_by_name and len(set(hb0)) == len(hb0) and sorted(hb0) == sorted(ha0)):
                    return "changed", [f"header: {b_rows[:1]} -> {a_rows[:1]}"]
                # A SQL result's columns are found by name: the same columns in another order are
                # the same result. The rows are put in the original's column order.
                pos = [ha0.index(c) for c in hb0]
                a_rows = [hb0] + [[r[i] if i < len(r) else "" for i in pos] for r in a_rows[1:]]
                reordered = True
                a_rows = [a_rows[0]] + sorted(a_rows[1:])  # SQL rows were sorted by their own column order
                b_rows = [b_rows[0]] + sorted(b_rows[1:])
            hb, rb = _normalise_csv(b_rows, opts)
            _, ra = _normalise_csv(a_rows, opts)
            details = _csv_details(hb, rb, ra, opts)
            if not details:
                return "same-data", (["the same columns in another order (SQL columns are compared by name)"]
                                     if reordered else
                                     ["every compared cell is equal (formatting, ignored columns, "
                                      "masked patterns, tolerance or row order differ)"])
            return "changed", details
    return _compare_text(before, after, opts)


def _csv_details(header: list[str], b: list[list[str]], a: list[list[str]], opts: CompareOptions) -> list[str]:
    details: list[str] = []
    if len(b) != len(a):
        details.append(f"row count: {len(b)} -> {len(a)}")
    for r, (rb, ra) in enumerate(zip(b, a), start=1):
        for c in range(max(len(rb), len(ra))):
            vb = rb[c] if c < len(rb) else "<missing>"
            va = ra[c] if c < len(ra) else "<missing>"
            if vb == va or (opts.numeric_forms and _same_number(vb, va)) or _both_zero(vb, va) \
                    or (opts.tolerance and _num_equal(vb, va, opts.tolerance)):
                continue
            name = header[c] if c < len(header) else f"col{c}"
            details.append(f"row {r}, {name}: {_short(vb)!r} -> {_short(va)!r}")
            if len(details) >= MAX_CELL_DIFFS:
                return details
    return details


def _compare_text(before: bytes, after: bytes, opts: CompareOptions) -> tuple[str, list[str]]:
    b = [_mask(x, opts.ignore_patterns) for x in before.decode("utf-8", errors="replace").splitlines()]
    a = [_mask(x, opts.ignore_patterns) for x in after.decode("utf-8", errors="replace").splitlines()]
    if opts.unordered:
        b, a = sorted(b), sorted(a)
    if b == a:
        return "same-data", ["equal after masking patterns, line endings or ordering"]
    diff = list(difflib.unified_diff(b, a, "original", "fix", lineterm="", n=0))
    return "changed", [_short(line, 120) for line in diff[:MAX_TEXT_LINES]]


def unstable_columns(first: bytes, second: bytes) -> tuple[set[str], str | None]:
    """Columns whose values differ between two runs of the original on the same input."""
    named_a, named_b = read_outputs(first), read_outputs(second)
    if named_a is not None and named_b is not None:
        if set(named_a) != set(named_b):
            return set(), "the outputs differ between two runs of the original"
        found: set[str] = set()
        for name in named_a:
            cols, note = unstable_columns(named_a[name], named_b[name])
            if note:
                return set(), f"{name}: {note}"
            found |= {f"{name}.{c}" for c in cols}
        return found, None
    first, second = _parquet_as_csv(first), _parquet_as_csv(second)
    a, b = parse_rows(first), parse_rows(second)
    if a is None or b is None:
        return set(), ("output is not CSV" if first != second else None)
    if a[:1] != b[:1] or len(a) != len(b):
        return set(), "header or row count differs between two runs of the original"
    header = a[0] if a else []
    unstable = set()
    for ra, rb in zip(a[1:], b[1:]):
        for i in range(max(len(ra), len(rb))):
            if (ra[i] if i < len(ra) else None) != (rb[i] if i < len(rb) else None):
                unstable.add(header[i] if i < len(header) else f"col{i}")
    return unstable, None
