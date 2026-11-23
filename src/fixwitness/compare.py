"""Compare what the original and the fix produced for the same input."""

from __future__ import annotations

import csv
import difflib
import io
import re
from dataclasses import dataclass, field

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


def compare(before: bytes, after: bytes, opts: CompareOptions) -> tuple[str, list[str]]:
    """Return (status, details). Status is 'identical', 'same-data' or 'changed'."""
    if before == after:
        return "identical", []
    if opts.mode == "csv":
        b_rows, a_rows = parse_rows(before), parse_rows(after)
        if b_rows is not None and a_rows is not None:
            if b_rows[:1] != a_rows[:1]:
                return "changed", [f"header: {b_rows[:1]} -> {a_rows[:1]}"]
            hb, rb = _normalise_csv(b_rows, opts)
            _, ra = _normalise_csv(a_rows, opts)
            details = _csv_details(hb, rb, ra, opts)
            if not details:
                return "same-data", ["every compared cell is equal (formatting, ignored columns, "
                                     "masked patterns, tolerance or row order differ)"]
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
            if vb == va or (opts.tolerance and _num_equal(vb, va, opts.tolerance)):
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
