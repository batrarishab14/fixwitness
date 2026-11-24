"""fixwitness benchmark for the 0.6 input kinds: which checks catch a wrong change?

Each case under benchmark/complex/ is a refactor task on one kind of code:

  pipeline   a dbt project (a folder of models), compared on its final model
  dialect    Snowflake SQL, translated with sqlglot
  pandas     a pandas function over two DataFrames
  polars     the pandas function migrated to polars
  json       a script reading JSON Lines
  parquet    a script reading and writing Parquet

Every fix is labelled correct or wrong, with the failure pattern it models: in its first two
lines (`-- label:` / `# label:`), or in label.txt for a folder of models. The wrong fixes are
synthetic. None was produced by an AI assistant.

Three ways to accept a fix are compared:

  job runs      the fix runs on the sample
  sample test   the above, and its output on the sample equals the original's
  fixwitness    fixwitness check

Cases whose libraries are not installed are skipped and listed.

Usage:
  python3 benchmark/run_complex_bench.py [--engine auto|duckdb|sqlite] [--only C03,C05]
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import subprocess
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from fixwitness import __version__  # noqa: E402
from fixwitness.compare import CompareOptions, compare  # noqa: E402
from fixwitness.config import load_config  # noqa: E402
from fixwitness.core import SQL_TOLERANCE, run_check  # noqa: E402
from fixwitness.plan import build_plan  # noqa: E402
from fixwitness.runner import run_side  # noqa: E402
from fixwitness.sql import choose_engine  # noqa: E402

CASES = HERE / "complex"
METHODS = ["job runs", "sample test", "fixwitness"]
NEEDS = {"pipeline": [], "dialect": ["sqlglot"], "pandas": ["pandas"], "polars": ["pandas", "polars"],
         "json": [], "parquet": ["pyarrow"]}
PATH_KEYS = {"sample", "incident", "incident_expected"}


def label_of(fix: Path) -> tuple[str, str]:
    source = fix / "label.txt" if fix.is_dir() else fix
    label, pattern = "unknown", ""
    for line in source.read_text(encoding="utf-8").splitlines()[:3]:
        text = line.lstrip("-# ").strip()
        if text.startswith("label:"):
            label = text.split(":", 1)[1].strip()
        elif text.startswith("pattern:"):
            pattern = text.split(":", 1)[1].strip()
    return label, pattern


def settings(meta: dict, fix: Path, engine: str) -> dict:
    d = meta["dir"]
    out = {"before": str(d / meta["original"]), "after": str(fix), "engine": engine}
    for key, value in meta.get("settings", {}).items():
        if key in PATH_KEYS:
            value = str(d / value)
        elif key in ("tables", "incident_tables"):
            value = {n: str(d / f) for n, f in value.items()}
        out[key] = value
    return out


def sample_checks(cfg) -> tuple[bool, bool]:
    """Run both sides on the sample only: does the fix run, and is its output the original's?"""
    with build_plan(cfg) as plan:
        d = plan.work / "bench"
        b = run_side(plan.invocation, plan.before, d, plan.sample)
        a = run_side(plan.fix_invocation, plan.after, d, plan.sample)
        runs = a.ok and a.output is not None
        opts = CompareOptions(mode=plan.output, tolerance=SQL_TOLERANCE if plan.sql is not None else 0.0,
                              unordered=cfg.unordered)
        same = runs and b.ok and b.output is not None and compare(b.output, a.output, opts)[0] != "changed"
        return runs, same


def run_all(engine: str, only: set[str] | None) -> tuple[list[dict], list[str]]:
    rows, skipped = [], []
    for case_dir in sorted(p for p in CASES.iterdir() if p.is_dir()):
        if only and case_dir.name.split("-", 1)[0] not in only:
            continue
        meta = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
        meta["dir"], meta["id"] = case_dir, case_dir.name
        missing = [m for m in NEEDS[meta["mode"]] if importlib.util.find_spec(m) is None]
        if missing:
            skipped.append(f"{meta['id']} (needs {', '.join(missing)})")
            print(f"{meta['id']:28} skipped: {', '.join(missing)} not installed", flush=True)
            continue
        maker = case_dir / "make_sample.py"
        if maker.exists():
            subprocess.run([sys.executable, str(maker)], check=True)
        for fix in sorted(p for p in (case_dir / "fixes").iterdir() if not p.name.startswith(".")):
            label, pattern = label_of(fix)
            cfg = load_config(None, settings(meta, fix, engine))
            runs, same = sample_checks(cfg)
            t0 = time.time()
            proof = run_check(cfg)
            rows.append({"case": meta["id"], "mode": meta["mode"], "fix": fix.name, "label": label,
                         "pattern": pattern, "job runs": runs, "sample test": same,
                         "fixwitness": proof["verdict"] == "PASS", "verdict": proof["verdict"],
                         "score": proof["confidence"]["score"], "cases": len(proof["cases"]),
                         "seconds": round(time.time() - t0, 1),
                         "reason": "; ".join(proof["reasons"]) or "-",
                         "caught_by": ", ".join(sorted({x["category"] for x in proof["differences"]
                                                        if x["kind"] != "review"})) or "-"})
            ok = rows[-1]["fixwitness"] == (label == "correct")
            print(f"{meta['id']:28} {fix.name:22} {label:8} runs={int(runs)} sample={int(same)} "
                  f"fw={proof['verdict']:12} {'ok' if ok else 'MISS'} ({rows[-1]['seconds']}s)", flush=True)
    return rows, skipped


def summarise(rows: list[dict], skipped: list[str], engine: str, seconds: float) -> str:
    wrong = [r for r in rows if r["label"] == "wrong"]
    right = [r for r in rows if r["label"] == "correct"]

    def caught(rs, m):
        return sum(1 for r in rs if not r[m])

    def pct(a, b):
        return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"

    out = ["# fixwitness benchmark: pipelines, dialects, DataFrames, JSON and Parquet", "",
           f"fixwitness {__version__} · SQL engine {engine} · {len(rows)} fixes across "
           f"{len({r['case'] for r in rows})} cases ({len(right)} correct, {len(wrong)} wrong) · "
           f"run time {seconds:.0f}s", "",
           "Development results: the cases were written in the same session as the 0.6 features. "
           "The wrong fixes are **synthetic**: each models a well-known pitfall, named per fix below. "
           "None was produced by an AI assistant.", ""]
    if skipped:
        out += ["Skipped (libraries not installed here): " + "; ".join(skipped) + ".", ""]
    out += ["| Check | Wrong fixes caught | Correct fixes wrongly rejected |", "|---|---|---|"]
    for m in METHODS:
        out.append(f"| {m} | {pct(caught(wrong, m), len(wrong))} | {pct(caught(right, m), len(right))} |")
    out += ["", "## Every fix", "",
            "| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | Caught by |",
            "|---|---|---|---|---|---|---|---|"]
    yes = {True: "accept", False: "**reject**"}
    for r in rows:
        out.append(f"| {r['case']} | {r['fix']} | {r['label']} | {r['pattern']} | {yes[r['job runs']]} | "
                   f"{yes[r['sample test']]} | {yes[r['fixwitness']]} | {r['caught_by']} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="auto", choices=["auto", "duckdb", "sqlite"])
    ap.add_argument("--only", help="comma-separated case ids, e.g. C01,C05")
    a = ap.parse_args()
    engine = choose_engine(a.engine)
    t0 = time.time()
    rows, skipped = run_all(engine, set(a.only.split(",")) if a.only else None)
    if not rows:
        print("no case could run")
        return 1
    suffix = "" if engine == "sqlite" else f"_{engine}"
    with (CASES / f"results{suffix}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (CASES / f"RESULTS{suffix}.md").write_text(summarise(rows, skipped, engine, time.time() - t0), encoding="utf-8")
    misses = [r for r in rows if r["fixwitness"] != (r["label"] == "correct")]
    print(f"{len(rows)} fixes, {len(misses)} where fixwitness disagrees with the label")
    return 0


if __name__ == "__main__":
    sys.exit(main())
