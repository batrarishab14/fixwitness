"""JSON, JSON Lines and Parquet: reading samples, generating cases, comparing outputs.

JSON and JSON Lines
    The sample is a JSON array of objects, an object holding one such array (an API response such
    as {"data": [...]}), or JSON Lines (one object per line). Cases change one value at a path such
    as ``customer.id`` or ``items[].sku`` (the first element of an array) in one record, the way
    CSV cases change one cell. JSON adds what CSV cannot express: a missing key, null, a number
    written as a string, nested objects and arrays, and key order.

Parquet
    The sample's columns and types are read with pyarrow. Cases are the typed-table cases of SQL
    mode, written back as Parquet with the sample's schema; a case the schema cannot hold (text in
    an integer column) is skipped, because a Parquet file cannot contain it.

Outputs that are JSON or Parquet are compared by value, not by bytes.
"""

from __future__ import annotations

import copy
import csv
import io
import json
import random
import re

from fixwitness.cases import (ATTACKS, CANARY_PREFIX, DATES, DEFAULT_KIND, QUOTES, SHELL_METACHAR, TEXT_CASE,
                              TEXT_LONG, TEXT_PUNCTUATION, TEXT_UNICODE, TEXT_WHITESPACE, Case, SampleError)

JSON_SUFFIXES = (".json", ".jsonl", ".ndjson")
PARQUET_MAGIC = b"PAR1"

# Raw JSON number literals: written into the file as they are, so the parser sees each spelling.
JSON_NUMBERS = ["0", "-0", "-3", "7", "1200", "1000000000000", "12.5", "12.50", "-12.75", "0.1", "1.0",
                "1e3", "1E3", "-1e3", "5e-2", "0.30000000000000004", "2.675", "1.005", "123456789.123",
                "9" * 30, "-0.0"]
JSON_ESCAPES = ["line\nbreak", "tab\tinside", "back\\slash", "slash/inside", 'quote "inside"', "é written \\u00e9"]
_RAW = "\x00fixwitness-raw:{}\x00"
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

JSON_CATEGORY_DESCRIPTIONS = {
    "missing-key": "a key left out of a record",
    "null": "a value set to null",
    "json-type": "a number written as a string, a numeric string written as a number, true/false as text",
    "json-escape": "escaped characters in strings: line breaks, tabs, backslashes, quotes, \\u escapes",
    "array": "an empty array, and an array with its first element repeated",
}


def is_json_name(name: str) -> bool:
    return name.lower().endswith(JSON_SUFFIXES)


def is_parquet(data: bytes | None) -> bool:
    return bool(data) and len(data) >= 8 and data[:4] == PARQUET_MAGIC and data[-4:] == PARQUET_MAGIC


# ---------------------------------------------------------------- JSON samples

class JsonShape:
    """How a sample holds its records, so a case is written back the same way."""

    def __init__(self, fmt: str, wrapper: dict | None, key: str | None, indent: int | None):
        self.fmt, self.wrapper, self.key, self.indent = fmt, wrapper, key, indent

    def dump(self, records: list) -> str:
        if self.fmt == "jsonl":
            return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
        body = records if self.wrapper is None else {**self.wrapper, self.key: records}
        return json.dumps(body, ensure_ascii=False, indent=self.indent) + "\n"


def parse_json_sample(sample: bytes) -> tuple[JsonShape, list[dict]]:
    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SampleError(f"sample is not UTF-8 text: {exc}") from exc
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = None
    if body is None or isinstance(body, dict) and not any(isinstance(v, list) for v in body.values()):
        lines = [ln for ln in text.splitlines() if ln.strip()]
        try:
            records = [json.loads(ln) for ln in lines]
        except json.JSONDecodeError as exc:
            raise SampleError(f"sample is neither JSON nor JSON Lines: {exc}") from exc
        if len(records) < 1 or not all(isinstance(r, dict) for r in records):
            raise SampleError("a JSON Lines sample needs one JSON object per line")
        return JsonShape("jsonl", None, None, None), records
    indent = 2 if "\n" in text.strip() else None
    if isinstance(body, list):
        if not body or not all(isinstance(r, dict) for r in body):
            raise SampleError("a JSON sample needs an array of objects (or an object holding one)")
        return JsonShape("json", None, None, indent), body
    if isinstance(body, dict):
        lists = [k for k, v in body.items() if isinstance(v, list) and v and all(isinstance(r, dict) for r in v)]
        if len(lists) != 1:
            raise SampleError("a JSON object sample must hold exactly one array of record objects "
                              f"(found {len(lists)}: {', '.join(lists) or 'none'})")
        key = lists[0]
        wrapper = {k: v for k, v in body.items() if k != key}
        return JsonShape("json", wrapper, key, indent), body[key]
    raise SampleError("a JSON sample needs an array of objects")


def _leaves(value, path: tuple = ()) -> list[tuple[tuple, object]]:
    """(path, value) for every value in a record; '[]' in a path means the array's first element."""
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            out.append((path + (k,), v))
            out += _leaves(v, path + (k,))
    elif isinstance(value, list) and value:
        out.append((path + ("[]",), value[0]))
        out += _leaves(value[0], path + ("[]",))
    return out


def path_name(path: tuple) -> str:
    name = ""
    for p in path:
        name += "[]" if p == "[]" else (("." if name else "") + p)
    return name


def json_paths(records: list[dict]) -> dict[str, str]:
    """Every path in the records and the JSON type it holds (number, string, date, boolean, object, array, null)."""
    types: dict[str, str] = {}
    for r in records:
        for path, v in _leaves(r):
            kind = ("boolean" if isinstance(v, bool) else "number" if isinstance(v, (int, float))
                    else "date" if isinstance(v, str) and _ISO_DATE.fullmatch(v)
                    else "string" if isinstance(v, str) else "object" if isinstance(v, dict)
                    else "array" if isinstance(v, list) else "null")
            name = path_name(path)
            if types.get(name) in (None, "null"):
                types[name] = kind
            elif types[name] != kind and kind != "null":
                types[name] = "mixed"
    return types


def _parent(record, path: tuple):
    """The container that holds the value at path (None if the path is not in this record)."""
    cur = record
    for p in path[:-1]:
        if p == "[]":
            if not isinstance(cur, list) or not cur:
                return None
            cur = cur[0]
        else:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
    last = path[-1]
    if last == "[]":
        return cur if isinstance(cur, list) and cur else None
    return cur if isinstance(cur, dict) and last in cur else None


_MISSING = object()


def _set(record, path: tuple, value) -> bool:
    holder = _parent(record, path)
    if holder is None:
        return False
    key = 0 if path[-1] == "[]" else path[-1]
    if value is _MISSING:
        if isinstance(holder, list):
            holder.pop(0)
        else:
            del holder[key]
    else:
        holder[key] = value
    return True


def _paths_by_name(records: list[dict]) -> dict[str, tuple]:
    found = {}
    for r in records:
        for path, _ in _leaves(r):
            found.setdefault(path_name(path), path)
    return found


def _value_plan(kind: str, current) -> list[tuple[str, object]]:
    """(category, new value) for one path; a raw number literal is ('raw', text)."""
    plan: list[tuple[str, object]] = [("missing-key", _MISSING), ("null", None)]
    if kind == "number":
        plan += [("numeric-format", ("raw", n)) for n in JSON_NUMBERS]
        plan += [("json-type", str(current))]
    elif kind in ("string", "date"):
        values = DATES if kind == "date" else []
        plan += [("date-format", v) for v in values]
        plan += [("empty", "")]
        plan += [("whitespace", v) for v in TEXT_WHITESPACE]
        plan += [("unicode", v) for v in TEXT_UNICODE]
        plan += [("case", v) for v in TEXT_CASE]
        if isinstance(current, str) and current.strip():
            plan += [("case", v) for v in dict.fromkeys((current.upper(), current.lower(), current.title()))
                     if v != current]
            plan += [("whitespace", " " + current), ("whitespace", current + " ")]
        plan += [("punctuation", v) for v in TEXT_PUNCTUATION]
        plan += [("long", v) for v in TEXT_LONG]
        plan += [("quotes", v) for v in QUOTES]
        plan += [("json-escape", v) for v in JSON_ESCAPES]
        plan += [("shell-metachar", v) for v in SHELL_METACHAR]
        if isinstance(current, str) and re.fullmatch(r"-?\d+(\.\d+)?", current.strip()):
            plan += [("json-type", ("raw", current.strip()))]
    elif kind == "boolean":
        plan += [("json-type", str(current).lower()), ("json-type", ("raw", "1" if current else "0"))]
    elif kind == "object":
        plan += [("empty", {})]
    elif kind == "array":
        plan += [("array", []), ("array", "<repeat first>")]
    return plan


def generate_json_cases(sample: bytes, columns: list[str] | None = None, rows: int = 3, max_cases: int = 300,
                        seed: int = 1337, review: list[str] | None = None, canary_dir: str | None = None,
                        attacks: bool = True, incident: bytes | None = None) -> list[Case]:
    shape, records = parse_json_sample(sample)
    base = [copy.deepcopy(r) for r in records[: max(1, rows)]]
    target = min(1, len(base) - 1)
    types = json_paths(base)
    paths = _paths_by_name(base)
    targets = columns or [n for n in types if types[n] != "null"]
    unknown = [c for c in targets if c not in types]
    if unknown:
        raise SampleError(f"path(s) not in the sample: {unknown}; the sample has {sorted(types)}")
    categories = dict(DEFAULT_KIND) | {c: "valid" for c in JSON_CATEGORY_DESCRIPTIONS}
    bad = [c for c in (review or []) if c not in categories]
    if bad:
        raise SampleError(f"unknown review categories {bad}; choose from {sorted(categories)}")
    kinds = categories | {c: "review" for c in (review or []) if c != "attack"}

    def write(recs: list, raws: dict[str, str] | None = None) -> bytes:
        text = shape.dump(recs)
        for token, literal in (raws or {}).items():
            text = text.replace(json.dumps(token, ensure_ascii=False), literal)
        return text.encode("utf-8")

    raw: list[tuple] = [("file-structure", None, "<sample as given>", sample, None),
                        ("file-structure", None, "<no records>", write([]), None)]
    if shape.fmt == "jsonl":
        raw.append(("file-structure", None, "<CRLF line endings>", write(base).replace(b"\n", b"\r\n"), None))
        raw.append(("file-structure", None, "<no final newline>", write(base).rstrip(b"\n"), None))
    else:
        other = JsonShape(shape.fmt, shape.wrapper, shape.key, None if shape.indent else 2)
        raw.append(("file-structure", None, "<compact JSON>" if shape.indent else "<indented JSON>",
                    other.dump(base).encode("utf-8"), None))
    # Schema: an extra key, keys in reverse order, and each key that is new in the incident file.
    extra = [copy.deepcopy(r) for r in base]
    name = "extra_field"
    while any(name in r for r in base):
        name += "_"
    extra[target][name] = "x"
    raw.append(("schema", None, f"<extra key {name}>", write(extra), None))
    raw.append(("schema", None, "<keys in reverse order>",
                write([dict(reversed(list(r.items()))) for r in base]), None))
    if incident is not None:
        try:
            _, inc_records = parse_json_sample(incident)
        except SampleError:
            inc_records = []
        known = set(types)
        for new_name, new_type in json_paths(inc_records).items():
            if new_name in known or "[]" in new_name or "." in new_name:
                continue
            value = next((r[new_name] for r in inc_records if new_name in r), None)
            recs = [copy.deepcopy(r) for r in base]
            recs[target][new_name] = value
            raw.append(("schema", new_name, f"<key from the incident: {new_name}>", write(recs), None))
    raw.append(("duplicate-row", None, "<first record repeated>", write([base[0]] + base), None))

    for col in targets:
        path = paths[col]
        current = _get(base[target], path)
        for category, value in _value_plan(types[col], current):
            recs = [copy.deepcopy(r) for r in base]
            raws = None
            if isinstance(value, tuple) and value[:1] == ("raw",):
                token = _RAW.format(len(raw))
                raws, value, shown = {token: value[1]}, token, value[1]
            elif value == "<repeat first>":
                arr = _get(recs[target], path)
                value, shown = (arr[:1] + arr) if isinstance(arr, list) else arr, "<first element repeated>"
            elif value is _MISSING:
                shown = "<key left out>"
            else:
                shown = json.dumps(value, ensure_ascii=False)
            if not _set(recs[target], path, value):
                continue
            raw.append((category, col, shown, write(recs, raws), None))
        if len(base) > 1 and types[col] not in ("object", "array"):
            other_value = _get(base[0], path)
            recs = [copy.deepcopy(r) for r in base]
            if other_value is not None and _set(recs[target], path, other_value):
                raw.append(("duplicate", col, json.dumps(other_value, ensure_ascii=False), write(recs), None))
        if attacks and types[col] in ("string", "date"):
            for spec in ATTACKS:
                raw.append(("attack", col, None, b"", spec))

    keep_always = ("file-structure", "attack")
    keep_first = ("schema", "missing-key", "null")
    if len(raw) > max_cases:
        keep = [i for i, r in enumerate(raw) if r[0] in keep_always]
        first = [i for i, r in enumerate(raw) if r[0] in keep_first]
        rest = [i for i, r in enumerate(raw) if r[0] not in keep_always + keep_first]
        budget = max(0, max_cases - len(keep))
        chosen = set(keep) | set(first[:budget])
        budget = max(0, budget - len(first))
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
            recs = [copy.deepcopy(r) for r in base]
            _set(recs[target], paths[col], value)
            content = write(recs)
        cases.append(Case(id=f"{i:03d}", category=category, kind=kinds[category], column=col, value=value,
                          content=content, family=family, oracle=oracle, canary=canary))
    return cases


def _get(record, path: tuple):
    holder = _parent(record, path)
    if holder is None:
        return None
    return holder[0] if path[-1] == "[]" else holder[path[-1]]


# ---------------------------------------------------------------- JSON outputs

def parse_json_output(data: bytes):
    """The value of a JSON output, or the list of values of a JSON Lines output; None if neither."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    try:
        return [json.loads(ln) for ln in lines]
    except json.JSONDecodeError:
        return None


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _key_path(path: str) -> str:
    """A path without array markers: "[].run_at" and "run_at" name the same key (one JSON Lines record
    parses as an object, several as a list)."""
    return ".".join(p for p in path.replace("[]", ".").split(".") if p)


def _drop(value, ignore: set[str], path: str = "", _norm: set[str] | None = None):
    norm = _norm if _norm is not None else {_key_path(i) for i in ignore}
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            p = f"{path}.{k}" if path else k
            if k in norm or _key_path(p) in norm:
                continue
            out[k] = _drop(v, ignore, p, norm)
        return out
    if isinstance(value, list):
        return [_drop(v, ignore, path + "[]", norm) for v in value]
    return value


def _mask_all(value, patterns):
    if not patterns:
        return value
    if isinstance(value, dict):
        return {k: _mask_all(v, patterns) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_all(v, patterns) for v in value]
    if isinstance(value, str):
        from fixwitness.compare import _mask
        return _mask(value, patterns)
    return value


def _sort_records(value):
    """Unordered comparison: the top-level array (or the array of an API-style object) as a multiset."""
    if isinstance(value, list):
        return sorted(value, key=_canon)
    if isinstance(value, dict):
        return {k: sorted(v, key=_canon) if isinstance(v, list) else v for k, v in value.items()}
    return value


def _diff(b, a, tol: float, path: str, out: list[str], limit: int) -> None:
    if len(out) >= limit:
        return
    where = path or "$"
    if isinstance(b, bool) or isinstance(a, bool):
        if b is not a:
            out.append(f"{where}: {_canon(b)[:60]} -> {_canon(a)[:60]}")
        return
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        if b != a and not (tol and abs(b - a) <= tol * max(1.0, abs(b), abs(a))):
            out.append(f"{where}: {b!r} -> {a!r}")
        return
    if isinstance(b, dict) and isinstance(a, dict):
        for k in list(b) + [k for k in a if k not in b]:
            p = f"{path}.{k}" if path else k
            if k not in a:
                out.append(f"{p}: key only in the original's output")
            elif k not in b:
                out.append(f"{p}: key only in the fix's output")
            else:
                _diff(b[k], a[k], tol, p, out, limit)
            if len(out) >= limit:
                return
        return
    if isinstance(b, list) and isinstance(a, list):
        if len(b) != len(a):
            out.append(f"{where}: {len(b)} items -> {len(a)} items")
        for i, (x, y) in enumerate(zip(b, a)):
            _diff(x, y, tol, f"{path}[{i}]", out, limit)
            if len(out) >= limit:
                return
        return
    if b != a or type(b) is not type(a):
        out.append(f"{where}: {_canon(b)[:60]} -> {_canon(a)[:60]}")


def compare_json(before: bytes, after: bytes, opts) -> tuple[str, list[str]] | None:
    """(status, details) when both outputs are JSON (or JSON Lines); None otherwise."""
    b, a = parse_json_output(before), parse_json_output(after)
    if b is None or a is None:
        return None
    b, a = _drop(b, opts.ignore_columns), _drop(a, opts.ignore_columns)
    b, a = _mask_all(b, opts.ignore_patterns), _mask_all(a, opts.ignore_patterns)
    if opts.unordered:
        b, a = _sort_records(b), _sort_records(a)
    details: list[str] = []
    _diff(b, a, opts.tolerance, "", details, 5)
    if details:
        return "changed", details
    return "same-data", ["every compared value is equal (formatting, key order, ignored keys, masked patterns, "
                         "tolerance or record order differ)"]


def unstable_json_paths(first: bytes, second: bytes) -> tuple[set[str], str | None] | None:
    """Keys whose values differ between two runs of the original; None when the output is not JSON."""
    a, b = parse_json_output(first), parse_json_output(second)
    if a is None or b is None:
        return None
    found: set[str] = set()

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                p = f"{path}.{k}" if path else k
                if k in x and k in y:
                    walk(x[k], y[k], p)
                else:
                    found.add(p)
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for u, v in zip(x, y):
                walk(u, v, path + "[]")
        elif x != y:
            found.add(path or "$")

    walk(a, b, "")
    if "$" in found or any(p.endswith("[]") for p in found):
        return set(), "the original's output changes between two runs on the same input"
    return {_key_path(p) for p in found}, None


# ---------------------------------------------------------------- Parquet

def _arrow():
    try:
        import pyarrow  # noqa: F401
        import pyarrow.parquet  # noqa: F401
    except ImportError:
        raise SampleError("Parquet needs pyarrow: pip install pyarrow") from None
    import pyarrow as pa
    import pyarrow.parquet as pq
    return pa, pq


def _kind(t) -> str:
    import pyarrow.types as at
    if at.is_integer(t):
        return "integer"
    if at.is_floating(t) or at.is_decimal(t):
        return "number"
    if at.is_date(t):
        return "date"
    return "text"


def parquet_table(data: bytes):
    pa, pq = _arrow()
    return pq.read_table(pa.BufferReader(data))


def parquet_to_csv(data: bytes, with_types: bool = False):
    """A Parquet file as CSV text (values written as SQL mode writes them), and its column kinds."""
    from fixwitness.sql import _cell
    table = parquet_table(data)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(table.column_names)
    cols = [table.column(i).to_pylist() for i in range(table.num_columns)]
    for r in zip(*cols) if cols else []:
        w.writerow([_cell(v) for v in r])
    text = buf.getvalue().encode("utf-8")
    if not with_types:
        return text
    return text, {f.name: _kind(f.type) for f in table.schema}, table.schema


def csv_to_parquet(text: bytes, schema) -> bytes | None:
    """CSV cells cast to the sample's Parquet schema; None when a value does not fit its column."""
    pa, pq = _arrow()
    import pyarrow.compute as pc
    rows = list(csv.reader(io.StringIO(text.decode("utf-8"), newline="")))
    header, body = rows[0], rows[1:]
    fields = {f.name: f for f in schema}
    arrays, out_fields = [], []
    for i, name in enumerate(header):
        cells = [r[i] if i < len(r) and r[i] != "" else None for r in body]
        f = fields.get(name) or pa.field(name, pa.string())
        try:
            arr = pa.array(cells, type=pa.string())
            if pa.types.is_floating(f.type) or pa.types.is_decimal(f.type) or pa.types.is_integer(f.type):
                arr = pa.array([None if c is None else c.strip() for c in cells], type=pa.string())
            arr = pc.cast(arr, f.type) if f.type != pa.string() else arr
        except (pa.ArrowInvalid, pa.ArrowNotImplementedError, pa.ArrowTypeError):
            return None
        arrays.append(arr)
        out_fields.append(pa.field(name, f.type, nullable=True))
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_arrays(arrays, schema=pa.schema(out_fields)), sink)
    return sink.getvalue().to_pybytes()


def generate_parquet_cases(sample: bytes, columns: list[str] | None = None, rows: int = 3, max_cases: int = 300,
                           seed: int = 1337, review: list[str] | None = None,
                           incident: bytes | None = None) -> list[Case]:
    from fixwitness.sql import generate_sql_cases, read_bundle
    text, kinds, schema = parquet_to_csv(sample, with_types=True)
    inc_text = parquet_to_csv(incident) if incident is not None and is_parquet(incident) else None
    cases = generate_sql_cases({"t": text}, {"t": kinds}, [f"t.{c}" for c in columns] if columns else None,
                               rows, max_cases, seed, review, {"t": inc_text} if inc_text else None)
    out = [Case(id="000", category="file-structure", kind=DEFAULT_KIND["file-structure"], column=None,
                value="<sample as given>", content=sample)]
    for c in cases:
        tables, _ = read_bundle(c.content)
        data = csv_to_parquet(tables["t"].encode("utf-8"), schema)
        if data is None:
            continue
        column = c.column[2:] if c.column and c.column.startswith("t.") else (None if c.column == "t" else c.column)
        out.append(Case(id=f"{len(out):03d}", category=c.category, kind=c.kind, column=column, value=c.value,
                        content=data))
    return out
