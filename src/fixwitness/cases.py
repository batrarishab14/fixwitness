"""Edge-case catalogue and test-case generation.

Every case is a small input file derived from the user's sample: the first few rows of the
sample with one cell replaced by an edge-case value. Running the original and the fixed
version on the same case, and comparing what they write, shows whether the fix changed
behaviour on inputs that real data feeds produce.

Three kinds of case:

* ``valid``  - realistic data. The fix must produce the same output as the original.
* ``review`` - categories the user has declared as "differences expected" (for example, the
               original's shell expansion of ``*`` *was* the vulnerability). Differences are
               reported for a human but do not fail the check.
* ``attack`` - injection payloads with an oracle: either a marker file the payload tries to
               create (command/code injection, path traversal) or a marker string that only
               appears if the payload was evaluated (template injection).
"""

from __future__ import annotations

import csv
import io
import random
import re
from dataclasses import dataclass, field

CANARY_PREFIX = "FIXWITNESS_CANARY_"
TEMPLATE_MARKER = "55433"  # 7 * 7919; appears in output only if a template payload was evaluated

NUMERIC_FORMATS = [
    "0", "-0", "+7", "-3", "10", "100", "1200", "2_500", "1000000000000",
    "1.0", "12.50", "-12.75", "99.99", "0.1", "0.001", "+0.5", "3.", ".5", "-0.0",
    "1e3", "1E3", "-1e3", "5e-2", "1_000", "1_000.5", "00", "123456789.123",
    "0.30000000000000004", "0.125", "2.675", "1.005", "-2.5", "0.5",
]
DATES = [
    "2026-01-01", "2026-12-31", "2024-02-29", "2000-02-29", "1999-12-31", "1970-01-01",
    "2026-1-5", "2026-01-5", "2026-1-05", "2026-06-15",
]
DATE_WHITESPACE = [" 2026-03-04", "2026-03-04 "]
_DATE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")
NUMERIC_WHITESPACE = [" 42 ", "\t7", "8 "]
NUMERIC_LONG = ["9" * 30]

TEXT_WHITESPACE = ["  padded  ", "multiple   spaces", "tab\tinside", "trailing ", "  leading", " "]
TEXT_UNICODE = ["Ünïcødé", "日本語", "emoji 📈", "café", "naïve", "Ελλάδα", "Straße", "İstanbul"]
TEXT_CASE = ["UPPER", "lower", "MiXeD", "Title Case"]
TEXT_PUNCTUATION = [
    "north-east", "a.b", "x_y", "50%", "A/B", "colon:here", "plus+sign", "at@sign", "equals=sign",
]
TEXT_LONG = ["x" * 5000]
CSV_STRUCTURE = ["comma, inside"]
QUOTES = ["O'Brien", 'say "hi"']
SHELL_METACHAR = ["*", "?", "[ab]", "$HOME", "${PATH}", "~", "back\\slash", "#hash", "semi;colon"]

# (family, template, oracle). {c} = absolute marker-file path; {up} = the same path reached with
# "../" from any working directory. A file oracle fires only if the marker file appears in the
# marker directory itself, so scripts that merely write files *named* after a value don't trigger it.
ATTACKS = [
    ("command-injection", "$(touch {c})", "file"),
    ("command-injection", "`touch {c}`", "file"),
    ("command-injection", "; touch {c}", "file"),
    ("command-injection", "x && touch {c}", "file"),
    ("command-injection", "| touch {c}", "file"),
    ("code-injection", "__import__('pathlib').Path('{c}').touch()", "file"),
    ("code-injection", "1 if __import__('pathlib').Path('{c}').touch() is None else 1", "file"),
    ("path-traversal", "{up}", "file"),   # ../../.. up to / and back down to the marker
    ("path-traversal", "{c}", "file"),    # an absolute path (os.path.join drops the base directory)
    ("template-injection", "{{{{7*7919}}}}", "output"),
    ("template-injection", "${{7*7919}}", "output"),
    ("template-injection", "#{{7*7919}}", "output"),
    ("template-injection", "<%= 7*7919 %>", "output"),
]

CATEGORY_DESCRIPTIONS = {
    "file-structure": "the sample itself, a header-only file, and CRLF line endings",
    "numeric-format": "integers, decimals, signs, exponents, underscores, leading zeros, rounding edges",
    "date-format": "valid dates, leap days and unpadded months/days",
    "duplicate": "a value copied from another row (duplicate keys)",
    "whitespace": "leading, trailing, repeated and tab whitespace",
    "empty": "an empty cell",
    "long": "a very long value",
    "unicode": "accented, non-Latin and emoji text",
    "case": "upper, lower and mixed case",
    "punctuation": "ordinary punctuation inside values",
    "csv-structure": "a comma inside a quoted CSV field",
    "quotes": "single and double quotes inside values",
    "shell-metachar": "glob, expansion and separator characters (* ? [ ] $ ~ \\ # ;)",
    "attack": "command/code injection, path traversal and template injection payloads",
}

DEFAULT_KIND = {name: "valid" for name in CATEGORY_DESCRIPTIONS}
DEFAULT_KIND["attack"] = "attack"


@dataclass
class Case:
    id: str
    category: str
    kind: str
    column: str | None
    value: str | None
    content: bytes = field(repr=False)
    family: str | None = None
    oracle: str | None = None      # "file" or "output" for attacks
    canary: str | None = None      # marker file name for file oracles


class SampleError(ValueError):
    pass


def _write_csv(header: list[str], rows: list[list[str]], line_ending: str = "\n") -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator=line_ending)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def is_numeric(values: list[str]) -> bool:
    seen = False
    for v in values:
        s = v.strip()
        if not s:
            continue
        try:
            float(s)
        except ValueError:
            return False
        seen = True
    return seen


def parse_sample(sample: bytes) -> tuple[list[str], list[list[str]]]:
    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SampleError(f"sample is not UTF-8 text: {exc}") from exc
    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise SampleError(f"sample is not valid CSV: {exc}") from exc
    if len(rows) < 2:
        raise SampleError("sample must be a CSV file with a header row and at least one data row")
    header, data = rows[0], rows[1:]
    width = len(header)
    data = [r + [""] * (width - len(r)) if len(r) < width else r for r in data]
    return header, data


def is_date(values: list[str]) -> bool:
    present = [v for v in values if v.strip()]
    return bool(present) and all(_DATE.fullmatch(v) for v in present)


def _type(values: list[str]) -> str:
    if is_numeric(values):
        return "numeric"
    if is_date(values):
        return "date"
    return "text"


def column_types(sample: bytes) -> dict[str, str]:
    header, data = parse_sample(sample)
    return {col: _type([r[i] for r in data]) for i, col in enumerate(header)}


def generate_cases(
    sample: bytes,
    columns: list[str] | None = None,
    rows: int = 3,
    max_cases: int = 300,
    seed: int = 1337,
    review: list[str] | None = None,
    canary_dir: str | None = None,
    attacks: bool = True,
) -> list[Case]:
    """Build the deterministic list of cases for a sample CSV."""
    header, data = parse_sample(sample)
    targets = columns or header
    missing = [c for c in targets if c not in header]
    if missing:
        raise SampleError(f"column(s) not in sample header {header}: {missing}")
    unknown = [c for c in (review or []) if c not in DEFAULT_KIND]
    if unknown:
        raise SampleError(f"unknown review categories {unknown}; choose from {sorted(DEFAULT_KIND)}")
    kinds = dict(DEFAULT_KIND)
    for c in review or []:
        if c != "attack":
            kinds[c] = "review"

    base = [list(r) for r in data[: max(1, rows)]]
    target_row = min(1, len(base) - 1)

    def with_value(col: str, value: str) -> bytes:
        idx = header.index(col)
        modified = [list(r) for r in base]
        modified[target_row][idx] = value
        return _write_csv(header, modified)

    # (category, column, value, content, attack-spec)
    raw: list[tuple] = [
        ("file-structure", None, "<sample as given>", sample, None),
        ("file-structure", None, "<header only>", _write_csv(header, []), None),
        ("file-structure", None, "<CRLF line endings>", _write_csv(header, base, "\r\n"), None),
    ]
    for col in targets:
        values = [r[header.index(col)] for r in data]
        kind = _type(values)
        if kind == "numeric":
            plan = [("numeric-format", NUMERIC_FORMATS), ("whitespace", NUMERIC_WHITESPACE),
                    ("empty", [""]), ("long", NUMERIC_LONG)]
        elif kind == "date":
            plan = [("date-format", DATES), ("whitespace", DATE_WHITESPACE), ("empty", [""])]
        else:
            plan = [("whitespace", TEXT_WHITESPACE), ("empty", [""]), ("unicode", TEXT_UNICODE),
                    ("case", TEXT_CASE), ("punctuation", TEXT_PUNCTUATION), ("long", TEXT_LONG),
                    ("csv-structure", CSV_STRUCTURE), ("quotes", QUOTES)]
        if len(base) > 1:
            plan.append(("duplicate", [base[0][header.index(col)]]))
        plan.append(("shell-metachar", SHELL_METACHAR))
        for category, vals in plan:
            for v in vals:
                raw.append((category, col, v, with_value(col, v), None))
        if attacks:
            for spec in ATTACKS:
                raw.append(("attack", col, None, b"", spec))

    # Cap the number of cases deterministically, always keeping file-structure and attack cases.
    if len(raw) > max_cases:
        keep = [i for i, r in enumerate(raw) if r[0] in ("file-structure", "attack")]
        rest = [i for i, r in enumerate(raw) if r[0] not in ("file-structure", "attack")]
        budget = max(0, max_cases - len(keep))
        chosen = set(keep) | set(random.Random(seed).sample(rest, min(budget, len(rest))))
        raw = [r for i, r in enumerate(raw) if i in chosen]

    cases: list[Case] = []
    for i, (category, col, value, content, spec) in enumerate(raw):
        family = oracle = canary = None
        if spec is not None:
            family, template, oracle = spec
            canary = f"{CANARY_PREFIX}{i:04d}_"
            marker_path = f"{canary_dir.rstrip('/')}/{canary}" if canary_dir else canary
            up = "../" * 12 + marker_path.lstrip("/")
            value = template.format(c=marker_path, up=up)
            content = with_value(col, value)
        cases.append(Case(id=f"{i:03d}", category=category, kind=kinds[category], column=col,
                          value=value, content=content, family=family, oracle=oracle, canary=canary))
    return cases
