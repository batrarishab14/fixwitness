"""Turn assistants' pasted answers to study/PROMPT_incidents.txt into benchmark agent fixes.

Input: a text file of answers, each preceded by a line
    RUN | <assistant> | model: <name> | run <n> | <date>
Each task's answer is either a fenced code block after its task ID, or (when the answer was
copied from the rendered chat) the task ID on its own line followed by the code.

Two copy problems are handled, and recorded in the `note` column; nothing else is changed:
  - a language label line ("Python") above the code, and explanation after the last task, are dropped;
  - code whose line breaks were lost in copying (one long line, indentation kept) gets its line
    breaks back. This is done only when it is exact: indented lines are split where their preserved
    indentation starts, the top-level lines must match the original program's except the `with` line,
    and removing the restored line breaks must give back the pasted text character for character.
Code whose indentation was lost cannot be restored without guessing and is reported, not imported.

Output: benchmark/agents/<assistant>-r<n>/<case-id>/fix.py for every task found, plus
study/runs_index.csv (assistant, model, run, date, case, file, found, note).

    python3 study/import_runs.py study/runs.txt
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIRS = {p.name: p for p in (ROOT / "benchmark" / "cases").iterdir() if p.name.startswith("I")}
CASES = sorted(CASE_DIRS)
RUN_LINE = re.compile(r"^\s*RUN\s*\|\s*(?P<assistant>[^|]+)\|\s*model:\s*(?P<model>[^|]*)\|\s*run\s*(?P<run>\d+)\s*\|\s*(?P<date>[^|\n]*)$",
                      re.I | re.M)
FENCE = re.compile(r"```[ \t]*([A-Za-z0-9]*)[^\n]*\n(.*?)```", re.S)
CASE_ID = re.compile(r"\b(I0[1-9])(?:-[a-z0-9-]+)?\b", re.I)
CASE_LINE = re.compile(r"^\s*(I0[1-9])(?:-[a-z0-9-]+)?\s*$", re.I)
LANG_LINE = re.compile(r"^\s*(python3?|py)\s*$", re.I)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def compiles(code: str) -> bool:
    try:
        compile(code, "<fix>", "exec")
        return True
    except SyntaxError:
        return False


def restore_line_breaks(line: str, case: str) -> str | None:
    """Exact inverse of 'all line breaks were deleted', or None if it cannot be shown to be exact."""
    original = (CASE_DIRS[case] / "original.py").read_text(encoding="utf-8").splitlines()
    first_indent = re.search(r"(?<! )(?= {2,})", line)
    if not first_indent:
        return None
    header, body = line[: first_indent.start()], line[first_indent.start():]
    out, rest = [], header
    for o in original:
        if o and o[0].isspace():
            break
        if o == "":
            out.append("")
        elif rest.startswith(o) and not o.startswith("with "):
            out.append(o)
            rest = rest[len(o):]
        elif o.startswith("with ") and rest.startswith("with "):
            out.append(rest)
            rest = ""
        else:
            return None
    if rest:
        return None
    out += [p for p in re.split(r"(?<! )(?= {2,})", body) if p]
    code = "\n".join(out) + "\n"
    if code.replace("\n", "") != line or not compiles(code):
        return None
    return code


def unfenced(body: str) -> dict[str, tuple[str, str]]:
    lines = body.splitlines()
    starts = [(i, m.group(1).upper()) for i, l in enumerate(lines) if (m := CASE_LINE.match(l))]
    found: dict[str, tuple[str, str]] = {}
    for k, (i, short) in enumerate(starts):
        case = next((c for c in CASES if c.startswith(short)), None)
        if not case or case in found:
            continue
        seg = lines[i + 1: starts[k + 1][0] if k + 1 < len(starts) else len(lines)]
        while seg and not seg[0].strip():
            seg.pop(0)
        notes = []
        if seg and LANG_LINE.match(seg[0]):
            seg.pop(0)
            notes.append("language label dropped")
        while seg and not seg[-1].strip():
            seg.pop()
        code = "\n".join(seg) + "\n"
        if len(seg) == 1 and not compiles(code):
            fixed = restore_line_breaks(seg[0], case)
            if fixed is None:
                found[case] = ("", "line breaks lost; could not be restored exactly")
                continue
            found[case] = (fixed, "; ".join(notes + ["line breaks restored (verified exact)"]))
            continue
        if not compiles(code):
            n = next((n for n in range(len(seg) - 1, 0, -1) if compiles("\n".join(seg[:n]) + "\n")), 0)
            tail = [l for l in seg[n:] if l.strip()]
            if n and tail and not tail[0][:1].isspace():
                print(f"  {case}: dropped {len(tail)} lines of explanation after the code, starting "
                      f"{tail[0][:60]!r}", file=sys.stderr)
                seg = seg[:n]
                while seg and not seg[-1].strip():
                    seg.pop()
                code = "\n".join(seg) + "\n"
                notes.append("explanation after the code dropped")
            else:
                found[case] = ("", "does not compile as pasted (indentation lost?); not imported")
                continue
        found[case] = (code, "; ".join(notes))
    return found


def fenced(body: str) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for b in FENCE.finditer(body):
        code = b.group(2)
        if "import" not in code and "def " not in code:
            continue
        ids = list(CASE_ID.finditer(body[: b.start()]))
        if not ids:
            continue
        short = ids[-1].group(1).upper()
        case = next((c for c in CASES if c.startswith(short)), None)
        if case and case not in found:
            found[case] = (code if code.endswith("\n") else code + "\n", "")
    return found


def main(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    marks = list(RUN_LINE.finditer(text))
    if not marks:
        print("no RUN lines found", file=sys.stderr)
        return 1
    index = []
    for i, m in enumerate(marks):
        body = text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        agent = f"{slug(m['assistant'])}-r{m['run']}"
        print(f"{m['assistant'].strip()} run {m['run']}:", file=sys.stderr)
        found = fenced(body) or unfenced(body)
        for case in CASES:
            code, note = found.get(case, ("", "not found"))
            row = {"assistant": m["assistant"].strip(), "model": m["model"].strip(), "run": m["run"],
                   "date": m["date"].strip().rstrip("."), "case": case, "file": "", "found": bool(code),
                   "note": note}
            if code:
                out = ROOT / "benchmark" / "agents" / agent / case / "fix.py"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(code, encoding="utf-8")
                row["file"] = str(out.relative_to(ROOT))
            index.append(row)
        print(f"  {sum(1 for c in CASES if found.get(c, ('',))[0])} of {len(CASES)} fixes imported", file=sys.stderr)
    with (ROOT / "study" / "runs_index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)
    got = sum(r["found"] for r in index)
    print(f"{len(marks)} runs, {got} of {len(index)} fixes found; see study/runs_index.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "study" / "runs.txt"))
