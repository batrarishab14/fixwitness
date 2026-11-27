"""fixwitness SQL benchmark: which checks catch a wrong change to a SQL query?

Each case under benchmark/sql/ has sample tables, an original query and a task: a refactor
(change nothing) or an incident (fix what broke, change nothing else). Each fix under fixes/
is labelled correct or wrong in its first line and names the failure pattern in its second.

Four ways to accept a fix are compared:

  job runs        the fixed query runs on the sample tables (and on the incident tables)
  sample test     the above, and its result on the sample tables equals the original's
                  -> what a data diff on today's data shows
  fixwitness      fixwitness check (no expected output)
  fixwitness+exp  fixwitness check with the expected result for the incident (incidents only)

Usage:
  python3 benchmark/run_sql_bench.py [--engine auto|duckdb|sqlite]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from fixwitness import __version__  # noqa: E402
from fixwitness.compare import CompareOptions, compare  # noqa: E402
from fixwitness.config import load_config  # noqa: E402
from fixwitness.core import run_check  # noqa: E402
from fixwitness.sql import choose_engine, make_bundle, run_query, table_types  # noqa: E402

CASES = HERE / "sql"
METHODS = ["job runs", "sample test", "fixwitness", "fixwitness+exp"]


def label_of(path: Path) -> tuple[str, str]:
    label, pattern = "unknown", ""
    for line in path.read_text(encoding="utf-8").splitlines()[:3]:
        if line.startswith("-- label:"):
            label = line.split(":", 1)[1].strip()
        elif line.startswith("-- pattern:"):
            pattern = line.split(":", 1)[1].strip()
    return label, pattern


def _try(sql: str, bundle: bytes, engine: str) -> bytes | None:
    try:
        return run_query(sql, bundle, engine)
    except Exception:
        return None


def baseline(meta: dict, fix: Path, engine: str) -> tuple[bool, bool]:
    d = meta["dir"]
    tables = {n: (d / f).read_bytes() for n, f in meta["tables"].items()}
    types = {n: table_types(b) for n, b in tables.items()}
    sample = make_bundle(tables, types)
    orig = _try((d / "original.sql").read_text(), sample, engine)
    out = _try(fix.read_text(), sample, engine)
    runs = out is not None
    if runs and meta.get("incident_tables"):
        inc = {**tables, **{n: (d / f).read_bytes() for n, f in meta["incident_tables"].items()}}
        runs = _try(fix.read_text(), make_bundle(inc, types), engine) is not None
    same = runs and orig is not None and compare(orig, out, CompareOptions(mode="csv"))[0] != "changed"
    return runs, same


def fixwitness(meta: dict, fix: Path, engine: str, expected: bool) -> dict:
    d = meta["dir"]
    overrides = {
        "before": str(d / "original.sql"), "after": str(fix),
        "tables": {n: str(d / f) for n, f in meta["tables"].items()},
        "review": meta.get("review", []), "engine": engine,
    }
    if meta.get("incident_tables"):
        overrides["incident_tables"] = {n: str(d / f) for n, f in meta["incident_tables"].items()}
        if expected:
            overrides["incident_expected"] = str(d / meta["expected"])
    return run_check(load_config(None, overrides))


def run_all(engine: str) -> list[dict]:
    rows = []
    for case_dir in sorted(p for p in CASES.iterdir() if p.is_dir()):
        meta = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
        meta["dir"], meta["id"] = case_dir, case_dir.name
        for fix in sorted((case_dir / "fixes").glob("*.sql")):
            label, pattern = label_of(fix)
            runs, same = baseline(meta, fix, engine)
            proof = fixwitness(meta, fix, engine, expected=False)
            proof_e = fixwitness(meta, fix, engine, expected=True) if meta.get("incident_tables") else proof
            rows.append({"case": meta["id"], "kind": meta["kind"], "fix": fix.name, "label": label,
                         "pattern": pattern, "job runs": runs, "sample test": same,
                         "fixwitness": proof["verdict"] == "PASS", "fixwitness+exp": proof_e["verdict"] == "PASS",
                         "score": proof_e["confidence"]["score"],
                         "reason": "; ".join(proof_e["reasons"]) or "-",
                         "caught_by": ", ".join(sorted({x["category"] for x in proof_e["differences"]
                                                        if x["kind"] != "review"})) or "-"})
            ok = rows[-1]["fixwitness+exp"] == (label == "correct")
            print(f"{meta['id']:34} {fix.name:22} {label:8} runs={int(runs)} sample={int(same)} "
                  f"fw={proof['verdict']:6} fw+exp={proof_e['verdict']:6} {'ok' if ok else 'MISS'}", flush=True)
    return rows


def summarise(rows: list[dict], engine: str, seconds: float) -> str:
    wrong = [r for r in rows if r["label"] == "wrong"]
    right = [r for r in rows if r["label"] == "correct"]

    def caught(rs, m):
        return sum(1 for r in rs if not r[m])

    def pct(a, b):
        return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"

    out = ["# fixwitness SQL benchmark results", "",
           f"fixwitness {__version__} · engine {engine} · {len(rows)} fixes across {len({r['case'] for r in rows})} "
           f"cases ({len(right)} correct, {len(wrong)} wrong) · run time {seconds:.0f}s", "",
           "The wrong fixes are **synthetic**: each models a well-known SQL pitfall, named per fix below. "
           "None was produced by an AI agent.", "",
           "| Check | Wrong fixes caught | Correct fixes wrongly rejected |", "|---|---|---|"]
    for m in METHODS:
        out.append(f"| {m} | {pct(caught(wrong, m), len(wrong))} | {pct(caught(right, m), len(right))} |")
    out += ["", "## Every fix", "",
            "| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | +exp | Caught by |",
            "|---|---|---|---|---|---|---|---|---|"]
    yes = {True: "accept", False: "**reject**"}
    for r in rows:
        out.append(f"| {r['case']} | {r['fix']} | {r['label']} | {r['pattern']} | {yes[r['job runs']]} | "
                   f"{yes[r['sample test']]} | {yes[r['fixwitness']]} | {yes[r['fixwitness+exp']]} | {r['caught_by']} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="auto", choices=["auto", "duckdb", "sqlite"])
    a = ap.parse_args()
    engine = choose_engine(a.engine)
    t0 = time.time()
    rows = run_all(engine)
    suffix = "" if engine == "sqlite" else f"_{engine}"
    with (CASES / f"results{suffix}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (CASES / f"RESULTS{suffix}.md").write_text(summarise(rows, engine, time.time() - t0), encoding="utf-8")
    print(f"wrote {CASES / f'RESULTS{suffix}.md'}")
    misses = [r for r in rows if r["fixwitness+exp"] == (r["label"] == "wrong")]
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
