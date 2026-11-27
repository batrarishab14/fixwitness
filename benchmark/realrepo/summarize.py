"""Write RESULTS.md for the real-repository study from the study-results branch.

    python benchmark/realrepo/summarize.py RESULTS_DIR

RESULTS_DIR holds results.csv (one row per candidate, from run_study.py) and commit.txt.
inspections.csv (next to this file) holds the reading of every refactor that fixwitness failed:
id, label (real / false-alarm), note. Rows without a reading are shown as "not yet read".
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"


def main() -> None:
    src = Path(sys.argv[1])
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "RESULTS.md"
    rows = list(csv.DictReader((src / "results.csv").open(encoding="utf-8")))
    cands = {r["id"]: r for r in csv.DictReader((HERE / "candidates.csv").open(encoding="utf-8"))}
    extra = {r["id"]: r for r in csv.DictReader((HERE / "after_freeze.csv").open(encoding="utf-8"))}
    reads = {}
    for f in (src / "inspections.csv", HERE / "inspections.csv"):  # the run's own reading first
        if f.is_file():
            reads = {r["id"]: r for r in csv.DictReader(f.open(encoding="utf-8"))}
            break
    commit = (src / "commit.txt").read_text(encoding="utf-8").strip() if (src / "commit.txt").is_file() else "?"
    frozen = [r for r in rows if r["id"] in cands]
    later = [r for r in rows if r["id"] in extra]
    bug = [r for r in frozen if r["set"] == "bug"]
    ref = [r for r in frozen if r["set"] == "refactor"]
    out = ["# Real-repository study: results", "",
           f"Run: `{commit}`. Protocol: [PROTOCOL.md](PROTOCOL.md). Candidates: [candidates.csv](candidates.csv), frozen "
           "before any run. One run per candidate, defaults only (`fixwitness check --base <parent> --no-attacks "
           "--warehouse postgres://...`).", ""]

    def table(title: str, group: list[dict], kinds: list[str]) -> None:
        count = Counter(r["outcome"] for r in group)
        checked = sum(count[k] for k in ("FAIL", "PASS"))
        out.extend([f"## {title}", "", "| Outcome | Count |", "|---|---|"])
        for k in kinds:
            out.append(f"| {k} | {count.get(k, 0)} |")
        out.append(f"| **checked** | **{checked}** of {len(group)} |")
        out.append("")

    table("Real bug fixes (would fixwitness have caught the bug?)", bug, ["FAIL", "PASS", "not checked"])
    caught = sum(1 for r in bug if r["outcome"] == "FAIL")
    checked = sum(1 for r in bug if r["outcome"] in ("FAIL", "PASS"))
    out += [f"**Caught: {pct(caught, checked)} of the checked bug fixes** (FAIL: some valid generated input gives "
            "a different output before and after the fix).", ""]
    by_label = Counter((r["label"], r["outcome"]) for r in bug)
    out += ["| Label | Caught | Missed | Not checked |", "|---|---|---|---|"]
    for label in ("wrong-data", "crash-on-data"):
        out.append(f"| {label} | {by_label[(label, 'FAIL')]} | {by_label[(label, 'PASS')]} | "
                   f"{by_label[(label, 'not checked')]} |")
    out.append("")

    table("Real refactors (does fixwitness raise false alarms?)", ref, ["PASS", "FAIL", "not checked"])
    fails = [r for r in ref if r["outcome"] == "FAIL"]
    real = [r for r in fails if reads.get(r["id"], {}).get("label") == "real"]
    false = [r for r in fails if reads.get(r["id"], {}).get("label") == "false-alarm"]
    unread = [r for r in fails if r["id"] not in reads]
    checked_ref = sum(1 for r in ref if r["outcome"] in ("FAIL", "PASS"))
    out += [f"**False alarms: {pct(len(false), checked_ref)} of the checked refactors.** Of {len(fails)} FAILs, "
            f"{len(real)} are real differences, {len(false)} false alarms"
            + (f", {len(unread)} not yet read" if unread else "") + ".", ""]
    if fails:
        out += ["| Refactor | Reading | What differs |", "|---|---|---|"]
        for r in fails:
            note = reads.get(r["id"], {})
            out.append(f"| `{r['id']}` | {note.get('label', 'not yet read')} | "
                       f"{(note.get('note') or r['first_finding'] or '').replace('|', '/')[:300]} |")
        out.append("")

    nc = [r for r in frozen if r["outcome"] == "not checked"]
    if nc:
        out += ["## Not checked, and why", "", "| Candidate | Set | Why |", "|---|---|---|"]
        for r in nc:
            out.append(f"| `{r['id']}` | {r['set']} | {(r['detail'] or '').replace('|', '/')[:220]} |")
        out.append("")
    if later:
        out += ["## Fixes after the list was frozen (reported apart)", "", "| Fix | Outcome | First finding |",
                "|---|---|---|"]
        for r in later:
            out.append(f"| `{r['id']}` ({extra[r['id']]['why']}) | {r['outcome']} | "
                       f"{(r['first_finding'] or r['detail'] or '').replace('|', '/')[:300]} |")
        out.append("")
    out += ["## Every candidate", "", "| Candidate | Set | Label | Outcome | Differences | Categories | Seconds |",
            "|---|---|---|---|---|---|---|"]
    for r in sorted(frozen, key=lambda r: (r["set"], r["id"])):
        out.append(f"| `{r['id']}` | {r['set']} | {r['label']} | {r['outcome']} | {r['differences']} | "
                   f"{r['categories']} | {r['seconds']} |")
    out.append("")
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"bug: caught {caught}/{checked} checked ({len(bug)} total); refactor: {len(fails)} FAIL "
          f"({len(false)} false alarms, {len(unread)} unread) of {checked_ref} checked ({len(ref)} total)")


if __name__ == "__main__":
    main()
