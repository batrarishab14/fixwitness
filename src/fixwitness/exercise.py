"""Was the changed code exercised by any input?

fixwitness compares the original and the changed code on generated inputs. When no input reaches the
code the change touched, both versions give the same output on every input, and that is not evidence
that the change is safe or that it fixes anything: it is no evidence at all. This module says so.

It works from two things only, so it does not depend on the engine (DuckDB, Postgres, pandas, a script):

  * what the change net-added or net-removed in the code: the literals it compares a value with
    (`= 'Accounts Payable'`, `in ('a', 'b')`, `like 'x%'`, `when 'x'`) and the names it uses;
  * what every input fixwitness generated contains: the value of every cell and, per column name,
    whether any cell is not empty.

It reports a finding only when it is certain of the fact it states:

  literal-absent  the change tests a value against 'x' and no cell of any input contains x
  guard-absent    the change sits in a query block whose WHERE keeps only rows equal to 'x' (no OR),
                  and no cell of any input contains x: no row reaches the changed code
  column-empty    the change names a data column that is empty in every input (in the tables the
                  changed code reads, when those are known)

Anything else (a join that never matches, rows that do not repeat, a range that no row falls in) is not
detected: "not exercisable" is reported when found, and silence is not a claim that the change was
exercised.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

MAX_CELL = 500                      # longer cells are cut: a literal is a short value
NULLS = {"", "null"}                # what counts as empty; only what is certainly empty

_SQL_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
_PY_COMMENT = re.compile(r"^[ \t]*#[^\n]*$", re.M)
_SQ = r"'((?:[^']|'')*)'"
_DQ = r'"((?:[^"\\\n]|\\.)*)"'
# A value compared for equality or matched against a pattern. Ranges (<, >, between) are left out: a
# range does not need its bound to be in the data.
_PRED = r"(?:==|!=|<>|(?<![<>!:=])=|\blike\b|\bilike\b|\bwhen\b)\s*"
_PRED_SQ = re.compile(_PRED + _SQ, re.I)
_IN = re.compile(r"\b(?:in|isin)\s*\(\s*[\(\[]?([^()\[\]]*)|\bin\s*\[([^()\[\]]*)", re.I)
_ANY_SQ = re.compile(_SQ)
_ANY_DQ = re.compile(_DQ)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PYTHON = re.compile(r"^\s*(def |import |from \w+ import )", re.M)
_SQL = re.compile(r"\bselect\b[\s\S]*\bfrom\b", re.I)
_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)  # config(...), ref(...), macros: not data
# In Python a single = binds a keyword argument (how="inner"), so only == and != compare.
_PRED_PY = r"(?:==|!=)\s*"
_PRED_DQ = re.compile(_PRED_PY + _DQ)
_PRED_SQ_PY = re.compile(_PRED_PY + _SQ)


def _clean(text: str, python: bool) -> str:
    return _PY_COMMENT.sub(" ", text) if python else _JINJA.sub(" ", _SQL_COMMENT.sub(" ", text))


def _language(text: str) -> str | None:
    """sql or python; anything else (shell, R, ...) is not read."""
    if _PYTHON.search(text):
        return "python"
    return "sql" if _SQL.search(text) else None


def _literal(value: str) -> str:
    return value.replace("''", "'").strip().casefold()


def _pred_literals(text: str, python: bool) -> Counter:
    """Each literal the code compares a value with, counted by how often."""
    out: Counter = Counter()
    for rx in ((_PRED_SQ_PY, _PRED_DQ) if python else (_PRED_SQ,)):
        for m in rx.finditer(text):
            out[_literal(m.group(1))] += 1
    for m in _IN.finditer(text):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        for rx in ((_ANY_SQ, _ANY_DQ) if python else (_ANY_SQ,)):
            for q in rx.finditer(body or ""):
                out[_literal(q.group(1))] += 1
    out.pop("", None)
    return out


def _all_literals(text: str, python: bool) -> Counter:
    out: Counter = Counter()
    for rx in ((_ANY_SQ, _ANY_DQ) if python else (_ANY_SQ,)):
        for m in rx.finditer(text):
            out[_literal(m.group(1))] += 1
    return out


def _names(text: str, python: bool) -> Counter:
    blanked = _ANY_SQ.sub(" ", text)
    if python:
        blanked = _ANY_DQ.sub(" ", blanked)
    return Counter(w.lower() for w in _IDENT.findall(blanked))


# ------------------------------------------------------------------ what the inputs contain

@dataclass
class Profile:
    values: set = field(default_factory=set)        # casefolded, stripped, non-empty cell values
    nonempty: dict = field(default_factory=dict)    # (table, column in lower case) -> any cell not empty
    inputs: int = 0                                 # how many inputs were read
    _seen: set = field(default_factory=set)

    def columns(self, name: str, tables: set | None = None) -> list[bool]:
        """Is the column non-empty, in each table that has it (only `tables`, if given)?"""
        return [v for (t, c), v in self.nonempty.items() if c == name and (not tables or t in tables)]


def _column_key(name: str) -> str:
    n = name.strip()
    if len(n) >= 2 and n[0] == n[-1] == '"':
        n = n[1:-1].replace('""', '"')
    return n.lower()


def _add_table(p: Profile, table: str, text: str) -> None:
    digest = hashlib.sha1(table.encode() + b"\0" + text.encode("utf-8", "replace")).digest()
    if digest in p._seen:
        return
    p._seen.add(digest)
    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error:
        return
    if not rows:
        return
    header = [_column_key(h) for h in rows[0]]
    for h in header:
        p.nonempty.setdefault((table, h), False)
    for row in rows[1:]:
        for h, cell in zip(header, row):
            v = cell.strip().casefold()
            if v in NULLS:
                continue
            p.nonempty[(table, h)] = True
            p.values.add(v[:MAX_CELL])


def profile_inputs(contents: Iterable[bytes]) -> Profile | None:
    """What a set of inputs contains: tables in fixwitness bundles, or CSV files. None when an input is
    in a format this does not read (JSON, Parquet), so nothing is claimed about it."""
    from fixwitness.sql import SqlError, is_bundle, read_bundle
    p = Profile()
    for data in contents:
        if data is None:
            continue
        try:
            if is_bundle(data):
                tables, _ = read_bundle(data)
                for name, text in tables.items():
                    _add_table(p, name, text)
            else:
                _add_table(p, "", data.decode("utf-8-sig"))
        except (SqlError, UnicodeDecodeError):
            return None
        p.inputs += 1
    return p if p.inputs else None


# ------------------------------------------------------------------ the filter above the change

_CLAUSE = re.compile(r"\b(where|having|qualify)\b(.*?)(?=\b(?:group\s+by|order\s+by|having|qualify|limit|union|"
                     r"window)\b|$)", re.S | re.I)
_OR = re.compile(r"\bor\b", re.I)
_EQ = re.compile(r"(?:==|(?<![<>!:=])=(?!=)|\blike\b|\bilike\b)\s*" + _SQ, re.I)
_NOT = re.compile(r"\bnot\s*$", re.I)


def _blocks(text: str) -> list[tuple[int, int]]:
    """Spans of the parenthesised sub-selects (`name as ( select ... )`), outermost last."""
    spans, stack, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "'":  # a string: skip it, '' being a quote inside it
            i += 1
            while i < n and not (text[i] == "'" and text[i + 1:i + 2] != "'"):
                i += 2 if text[i] == "'" else 1
        elif c == "(":
            stack.append(i)
        elif c == ")" and stack:
            o = stack.pop()
            if re.match(r"\s*(select|with)\b", text[o + 1:o + 40], re.I):
                spans.append((o + 1, i))
        i += 1
    return sorted(spans, key=lambda s: s[1] - s[0])


_OPENS_BLOCK = re.compile(r"\(\s*(?:select|with)\b", re.I)


def _changed_offsets(old: str, new: str) -> tuple[list[int], list[int]]:
    """Where each version's text starts to differ: character offsets of the lines the change touched."""
    import difflib
    ol, nl = old.splitlines(keepends=True), new.splitlines(keepends=True)
    starts = lambda lines: [sum(map(len, lines[:i])) for i in range(len(lines) + 1)]  # noqa: E731
    so, sn = starts(ol), starts(nl)
    a, b = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ol, nl, autojunk=False).get_opcodes():
        if tag != "equal":
            # a line that itself opens a sub-select: which block it belongs to is not clear, so no claim
            a += [so[i] for i in range(i1, max(i2, i1 + 1)) if i < len(so)
                  and not (i < len(ol) and _OPENS_BLOCK.search(ol[i]))]
            b += [sn[j] for j in range(j1, max(j2, j1 + 1)) if j < len(sn)
                  and not (j < len(nl) and _OPENS_BLOCK.search(nl[j]))]
    return a, b


def _guards(text: str, offsets: list[int]) -> set[str]:
    """Values the WHERE of each query block holding a changed line keeps rows equal to (no OR)."""
    found: set[str] = set()
    blocks = _blocks(text)
    for off in offsets:
        span = next(((s, e) for s, e in blocks if s <= off <= e), (0, len(text)))
        for m in _CLAUSE.finditer(text[span[0]:span[1]]):
            clause = m.group(2)
            if _OR.search(clause):
                continue  # one of several ways to qualify: a value nobody has proves nothing
            for q in _EQ.finditer(clause):
                found.add(_literal(q.group(1)))
            for q in _IN.finditer(clause):
                if _NOT.search(clause[:q.start()]):
                    continue
                body = q.group(1) if q.group(1) is not None else q.group(2)
                found |= {_literal(x.group(1)) for x in _ANY_SQ.finditer(body or "")}
    found.discard("")
    return found


# ------------------------------------------------------------------ the change

def _expand(name: str, renames: dict[str, set[str]]) -> set[str]:
    """A name and the column names it was renamed from (`id as order_id`), through a few layers."""
    names = {name}
    for _ in range(3):
        names |= {src for n in list(names) for src in renames.get(n, ())}
    return names


def assess(before: str | None, after: str | None, everything: str, profile: Profile | None,
           renames: dict[str, set[str]] | None = None, tables: set[str] | None = None) -> dict:
    """Findings about the code the change touched, against what the inputs contain.

    `before` and `after` are the code that changed (the changed models, or the changed file);
    `everything` is all the code of both versions, for telling a value the query produces itself
    (`'bill' as type`) from one that must come from the data. `tables` are the tables the changed code
    reads, when known: a column is "empty" only there.
    """
    result = {"assessed": False, "exercisable": None, "findings": [], "literals_checked": 0,
              "columns_checked": 0}
    if profile is None or before is None or after is None or before == after:
        return result
    lang = _language(before)
    if lang is None or lang != _language(after):
        return result  # a rewrite into another language, or code that is not SQL or Python: no claim
    python = lang == "python"
    b, a, whole = _clean(before, python), _clean(after, python), _clean(everything, python)
    result["assessed"] = True
    findings = []

    pb, pa = _pred_literals(b, python), _pred_literals(a, python)
    wanted = {k: "literal-absent" for k in set(pb) | set(pa) if pb[k] != pa[k]}
    nb0, na0 = _names(b, python), _names(a, python)
    if not python and (nb0 != na0 or pb != pa):  # something was added or removed, not only moved
        for text, offsets in ((b, _changed_offsets(b, a)[0]), (a, _changed_offsets(b, a)[1])):
            for k in _guards(text, offsets):
                wanted.setdefault(k, "guard-absent")
    all_whole, pred_whole = _all_literals(whole, python), _pred_literals(whole, python)
    for lit, kind in sorted(wanted.items()):
        if all_whole[lit] > pred_whole[lit]:
            continue  # the code also writes this value somewhere: it may produce it, not read it
        needle = lit.strip("%_ ")
        if not needle:
            continue
        result["literals_checked"] += 1
        if not any(needle in v for v in profile.values):
            what = ("the change tests a value against" if kind == "literal-absent"
                    else "the change sits under a filter that keeps only rows equal to")
            findings.append({"kind": kind, "name": lit,
                             "detail": f"{what} {lit!r}, but no cell of any of the {profile.inputs} inputs "
                                       "contains it"})

    nb, na = _names(b, python), _names(a, python)
    renames = renames or {}
    for name in sorted(k for k in set(nb) | set(na) if nb[k] != na[k]):
        states = [v for k in _expand(name, renames) for v in profile.columns(k, tables)]
        if not states:
            continue  # not a data column
        result["columns_checked"] += 1
        if not any(states):
            findings.append({"kind": "column-empty", "name": name,
                             "detail": f"the change uses column {name!r}, but it is empty in every one of the "
                                       f"{profile.inputs} inputs"})
    result["findings"] = findings
    result["exercisable"] = not findings
    return result


def summary(result: dict, limit: int = 3) -> str:
    """One sentence for the report's reasons."""
    items = result["findings"]
    names = ", ".join(f"column {f['name']}" if f["kind"] == "column-empty" else f"{f['name']!r}"
                      for f in items[:limit])
    more = f" and {len(items) - limit} more" if len(items) > limit else ""
    return ("not exercisable with this data: no input reaches what the change touched "
            f"({names}{more}), so identical output proves nothing about it; add rows that have it")
