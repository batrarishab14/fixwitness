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

# Characters other programs use as CSV delimiters. A fix that guesses the delimiter from the data
# can be fooled by them when they appear in a header or a value of a comma file.
ALT_DELIMITERS = [";", "\t", "|"]
# Another delimiter character combined with quotes, or repeated.
DELIMITER_MIX = [v for d in ALT_DELIMITERS for v in (f'a{d} "b"', f'"a"{d} b', f"a{d}b{d}c")]
# A delimiter-mix value is made of characters from these categories, so it follows their review
# setting: if the user expects differences on shell metacharacters or quotes, it is reviewed too.
SHELL_CHARS = set(";|&$*?[]~#\\`<>()")
QUOTE_CHARS = set("\"'")


def related_categories(value: str) -> set[str]:
    found = set()
    if any(ch in SHELL_CHARS for ch in value):
        found.add("shell-metachar")
    if any(ch in QUOTE_CHARS for ch in value):
        found.add("quotes")
    return found


# Names for an added column that a program reading columns by name should ignore.
HEADER_NAME_EXTRAS = ['say "hi"', "last, first", " padded ", "Ünïcødé", ""]

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
    "schema": "an extra column (including each column that is new in the incident file) and reordered columns",
    "header-names": "an added column whose name holds other delimiter characters (; tab |), quotes, a comma, "
                    "a line break, spaces, Unicode, or nothing; placed first and last",
    "delimiter-mix": "values that combine another delimiter character (; tab |) with quotes, written quoted and "
                     "unquoted; reviewed instead of failed when shell-metachar or quotes is under review",
    "null-column": "every value in one column empty (NULL once loaded into SQL)",
    "duplicate-row": "a whole row repeated",
    "pairs": "two rows of the same group, each with an unusual value (sub-cent amounts, precision edges, "
             "another case), so the two values are combined",
    "attack": "command/code injection, path traversal and template injection payloads",
}

# When the number of cases is capped: always keep these, then fill the budget with the
# structural categories before sampling the rest at random.
ALWAYS_KEEP = ("file-structure", "attack")
KEEP_FIRST = ("schema", "header-names")

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


def _write_unquoted(header: list[str], rows: list[list[str]]) -> bytes | None:
    """Write without CSV quoting, as many exporters do. None if a cell needs quoting to stay one cell."""
    lines = []
    for r in [header] + rows:
        if any("," in c or "\n" in c or "\r" in c or c.startswith('"') for c in r):
            return None
        lines.append(",".join(r))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _parse_any(data: bytes | None) -> tuple[list[str], list[list[str]]] | None:
    """Best-effort read of another CSV file (the incident input), with any common delimiter."""
    if not data:
        return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    best = None
    for d in [","] + ALT_DELIMITERS:
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=d))
        except csv.Error:
            continue
        if rows and len(rows[0]) > 1 and (best is None or len(rows[0]) > len(best[0])):
            best = rows
    if best is None or len(best) < 1:
        return None
    return best[0], best[1:]


def _fresh(name: str, header: list[str]) -> str:
    """The name, made unique against the existing header (a duplicate name would test something else)."""
    new, k = name, 2
    while new in header:
        new, k = f"{name}_{k}", k + 1
    return new


def _schema_cases(header: list[str], base: list[list[str]], incident: bytes | None) -> list[tuple]:
    """Files with the same data but a different set or order of columns.

    A program that reads columns by name ignores extra columns and column order. A fix that
    prefers a new column when it is present, or that switches to reading by position, gives a
    different result on such a file, even though the original handled it.
    """
    out: list[tuple] = []
    n = len(base)

    def add(label: str, new_header: list[str], new_rows: list[list[str]]) -> None:
        out.append(("schema", None, label, _write_csv(new_header, new_rows), None))

    extra = _fresh("extra", header)
    add("<extra column at the end>", header + [extra], [r + ["1"] for r in base])
    add("<extra column at the start>", [extra] + header, [["1"] + r for r in base])
    if len(header) > 1:
        order = list(reversed(range(len(header))))
        add("<columns in reverse order>", [header[i] for i in order], [[r[i] for i in order] for r in base])
    if len(header) > 2:
        order = list(range(1, len(header))) + [0]
        add("<first column moved to the end>", [header[i] for i in order], [[r[i] for i in order] for r in base])

    parsed = _parse_any(incident)
    if parsed:
        inc_header, inc_rows = parsed
        new_cols = [i for i, c in enumerate(inc_header) if c not in header]
        if new_cols and inc_rows:
            def values(i: int, k: int) -> str:
                row = inc_rows[k % len(inc_rows)]
                return row[i] if i < len(row) else ""
            groups = ([new_cols] if len(new_cols) > 1 else []) + [[i] for i in new_cols]
            for g in groups:
                names = [inc_header[i] for i in g]
                add("<incident column(s) " + ", ".join(names) + " added>",
                    header + names, [r + [values(i, k) for i in g] for k, r in enumerate(base[:n])])
    return out


def _header_name_cases(header: list[str], base: list[list[str]]) -> list[tuple]:
    """An added column whose name contains characters that confuse delimiter or header detection."""
    out: list[tuple] = []
    k = len(header) + 1          # more of each character than the commas in the new header line
    names = []
    for d in ALT_DELIMITERS:
        names.append(("c" + d) * k + "c")   # e.g. c;c;c;c;c
        names.append("c" + d + "\nc")       # a line break inside the header record
    names += HEADER_NAME_EXTRAS
    for name in (_fresh(n, header) for n in names):
        shown = name.replace("\n", "\\n").replace("\t", "\\t")
        out.append(("header-names", None, f"<column '{shown}' added at the end>",
                    _write_csv(header + [name], [r + ["x"] for r in base]), None))
        out.append(("header-names", None, f"<column '{shown}' added at the start>",
                    _write_csv([name] + header, [["x"] + r for r in base]), None))
    return out


UNQUOTED = " (unquoted)"
IN_NOTE = " (in an added 'note' column)"
IN_NOTE_UNQUOTED = " (in an added 'note' column, unquoted)"


def _base_value(label: str) -> str:
    for suffix in (IN_NOTE_UNQUOTED, IN_NOTE, UNQUOTED):
        if label.endswith(suffix):
            return label[: -len(suffix)]
    return label


def _delimiter_mix_cases(header: list[str], base: list[list[str]], target_row: int,
                         text_columns: list[str]) -> list[tuple]:
    """Values combining another delimiter character with quotes, quoted and unquoted.

    Written into each probed text column, and into an added text column, so that jobs whose
    probed columns are all numeric are covered too.
    """
    out: list[tuple] = []
    for v in DELIMITER_MIX:
        for col in text_columns:
            idx = header.index(col)
            rows = [list(r) for r in base]
            rows[target_row][idx] = v
            out.append(("delimiter-mix", col, v, _write_csv(header, rows), None))
            raw = _write_unquoted(header, rows)
            if raw is not None:
                out.append(("delimiter-mix", col, v + UNQUOTED, raw, None))
        note = _fresh("note", header)
        rows = [r + ["note"] for r in base]
        rows[target_row][-1] = v
        out.append(("delimiter-mix", None, v + IN_NOTE, _write_csv(header + [note], rows), None))
        raw = _write_unquoted(header + [note], rows)
        if raw is not None:
            out.append(("delimiter-mix", None, v + IN_NOTE_UNQUOTED, raw, None))
    return out


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


# Pairs of values for two rows of the same group: rounding each value differs from rounding their
# sum (0.005 + 0.005, 2.675 + 1.005), floating-point sums are not exact (0.1 + 0.2), signs cancel,
# and integers beyond 2**53 lose precision when converted to float.
PAIR_NUMBERS = [("0.005", "0.005"), ("2.675", "1.005"), ("0.1", "0.2"), ("-0.5", "0.5"),
                ("9007199254740993", "1")]


def pair_values(kind: str, current: str) -> list[tuple[str, str]]:
    if kind == "numeric":
        return PAIR_NUMBERS
    if kind == "text" and current.strip():
        return [(current, current.upper() if current.upper() != current else current.lower()),
                (current, current + " ")]
    return []


def paired_rows(base: list[list[str]], target: int, idx: int, a: str, b: str) -> list[list[str]]:
    """The target row with value a, and a copy of it (same group) with value b right after it."""
    rows = [list(r) for r in base]
    rows[target][idx] = a
    twin = list(rows[target])
    twin[idx] = b
    return rows[: target + 1] + [twin] + rows[target + 1:]


def focus_columns(before: str | None, after: str | None, columns: list[str]) -> list[str]:
    """The columns named in the lines the change touched (diff-aware cases)."""
    if before is None or after is None or before == after:
        return []
    import difflib
    changed = [ln[1:] for ln in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
               if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", "\n".join(changed)))
    return [c for c in columns if c.rsplit(".", 1)[-1] in words]


def generate_cases(
    sample: bytes,
    columns: list[str] | None = None,
    rows: int = 3,
    max_cases: int = 300,
    seed: int = 1337,
    review: list[str] | None = None,
    canary_dir: str | None = None,
    attacks: bool = True,
    incident: bytes | None = None,
    focus: list[str] | None = None,
) -> list[Case]:
    """Build the deterministic list of cases for a sample CSV (and, for repairs, its incident file)."""
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
    raw += _schema_cases(header, base, incident)
    raw += _header_name_cases(header, base)
    text_columns = [c for c in targets if _type([r[header.index(c)] for r in data]) == "text"]
    raw += _delimiter_mix_cases(header, base, target_row, text_columns)
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
        idx = header.index(col)
        for a, b in pair_values(kind, base[target_row][idx]):
            raw.append(("pairs", col, f"{a} | {b}", _write_csv(header, paired_rows(base, target_row, idx, a, b)), None))
        if attacks:
            for spec in ATTACKS:
                raw.append(("attack", col, None, b"", spec))

    # Cap the number of cases deterministically: file-structure and attack cases always stay,
    # then the structural cases, then a seeded random sample of the rest.
    if len(raw) > max_cases:
        focused = set(focus or [])
        keep = [i for i, r in enumerate(raw) if r[0] in ALWAYS_KEEP]
        first = [i for i, r in enumerate(raw) if r[0] in KEEP_FIRST]
        near = [i for i, r in enumerate(raw) if r[0] not in ALWAYS_KEEP + KEEP_FIRST and r[1] in focused]
        rest = [i for i, r in enumerate(raw) if r[0] not in ALWAYS_KEEP + KEEP_FIRST and r[1] not in focused]
        budget = max(0, max_cases - len(keep))
        chosen = set(keep) | set(first[:budget])
        budget = max(0, budget - len(first))
        chosen |= set(near[:budget])  # the columns the change touched keep all their cases
        budget = max(0, budget - len(near))
        chosen |= set(random.Random(seed).sample(rest, min(budget, len(rest))))
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
        kind = kinds[category]
        if category == "pairs" and value is not None:
            # The twin repeats every other value of its row, so it repeats the row's keys (a duplicate
            # key), and with two equal values it is an exact repeat of the row: it is reviewed when
            # those are.
            same = len(set(value.split(" | "))) == 1
            if kinds["duplicate"] == "review" or (same and kinds["duplicate-row"] == "review"):
                kind = "review"
        if category == "delimiter-mix" and kind == "valid" and value is not None \
                and any(kinds.get(c) == "review" for c in related_categories(_base_value(value))):
            kind = "review"
        cases.append(Case(id=f"{i:03d}", category=category, kind=kind, column=col,
                          value=value, content=content, family=family, oracle=oracle, canary=canary))
    return cases
