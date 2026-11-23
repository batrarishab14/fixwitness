"""fixwitness benchmark: how often do the usual checks accept a wrong fix, and how often does fixwitness?

Every case has an original script, a sample of normal data and a task (a security finding, an
incident that broke the job, or a refactor request). Each fix under cases/<id>/fixes/ is labelled
correct or wrong in its first line; agent-generated fixes go under agents/<agent>/<id>/ and are
evaluated without a label.

Four ways to accept a fix are compared:

  job runs        the fix runs on the sample (and on the incident input) without an error
                  -> what "the pipeline is green" or "dbt build passed" checks
  sample test     the above, and its output on the sample equals the original's
                  -> a regression test on the data you have
  fixwitness      fixwitness check (no expected output)
  fixwitness+exp  fixwitness check with the expected output for the incident input (incidents only)

Usage:
  python3 benchmark/run_bench.py              # run everything, write results.csv and RESULTS.md
  python3 benchmark/run_bench.py prompts      # write cases/<id>/PROMPT.md for running real agents
"""

from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import time
import tomllib
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from fixwitness import __version__  # noqa: E402
from fixwitness.compare import CompareOptions, compare  # noqa: E402
from fixwitness.config import load_config  # noqa: E402
from fixwitness.core import run_check  # noqa: E402
from fixwitness.runner import Invocation, Side, run_side  # noqa: E402

CASES = HERE / "cases"
AGENTS = HERE / "agents"
METHODS = ["job runs", "sample test", "fixwitness", "fixwitness+exp"]


def load_case(case_dir: Path) -> dict:
    meta = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
    meta["dir"] = case_dir
    meta["id"] = case_dir.name
    return meta


def label_of(path: Path) -> tuple[str, str]:
    label, pattern = "unknown", ""
    for line in path.read_text(encoding="utf-8").splitlines()[:3]:
        if line.startswith("# label:"):
            label = line.split(":", 1)[1].strip()
        elif line.startswith("# pattern:"):
            pattern = line.split(":", 1)[1].strip()
    return label, pattern


def agent_labels() -> dict[tuple[str, str], str]:
    """Labels for agent fixes from the assistant study (study/labels.csv), if present."""
    path = HERE.parent / "study" / "labels.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {(r["agent"], r["case"]): r["label"] for r in csv.DictReader(fh)}


def fixes_for(meta: dict) -> list[tuple[str, Path]]:
    found = [("benchmark", p) for p in sorted((meta["dir"] / "fixes").iterdir()) if p.is_file()]
    if AGENTS.is_dir():
        for agent in sorted(p for p in AGENTS.iterdir() if p.is_dir()):
            folder = agent / meta["id"]
            if folder.is_dir():
                found += [(f"agent:{agent.name}", p) for p in sorted(folder.iterdir())
                          if p.is_file() and p.suffix in (".py", ".sh")]
    return found


def baseline(meta: dict, fix: Path) -> tuple[bool, bool, str]:
    """The checks teams rely on today: does it run, and does it match on the sample?"""
    inv = Invocation(template=meta["run"], timeout=10)
    original = Side("original", None, (meta["dir"] / meta["script"]).resolve())
    fixed = Side("fix", None, fix.resolve())
    sample = (meta["dir"] / "sample.csv").read_bytes()
    with tempfile.TemporaryDirectory(prefix="fwbench-") as tmp:
        d = Path(tmp)
        r_orig = run_side(inv, original, d / "o", sample)
        r_fix = run_side(inv, fixed, d / "f", sample)
        runs = r_fix.ok and r_fix.output is not None
        why = "" if runs else "fails on the sample"
        if runs and meta.get("incident"):
            r_inc = run_side(inv, fixed, d / "i", (meta["dir"] / meta["incident"]).read_bytes())
            runs = r_inc.ok and r_inc.output is not None
            why = "" if runs else "still fails on the incident input"
        same = runs and r_orig.output is not None and \
            compare(r_orig.output, r_fix.output, CompareOptions(mode="csv"))[0] != "changed"
        if runs and not same:
            why = "output on the sample differs"
    return runs, same, why


def fixwitness(meta: dict, fix: Path, expected: bool) -> dict:
    d = meta["dir"]
    overrides = {
        "before": str(d / meta["script"]), "after": str(fix), "sample": str(d / "sample.csv"),
        "run": meta["run"], "columns": meta.get("columns"), "review": meta.get("review", []),
        "attacks": meta["kind"] == "security", "output": "csv",
    }
    if meta.get("incident"):
        overrides["incident"] = str(d / meta["incident"])
        if expected:
            overrides["incident_expected"] = str(d / meta["expected"])
    return run_check(load_config(None, overrides))


def run_all() -> list[dict]:
    rows = []
    agent_label = agent_labels()
    for case_dir in sorted(p for p in CASES.iterdir() if p.is_dir()):
        meta = load_case(case_dir)
        for source, fix in fixes_for(meta):
            label, pattern = label_of(fix) if source == "benchmark" else \
                (agent_label.get((source[6:], meta["id"]), "unknown"), "")
            runs, same, why = baseline(meta, fix)
            proof = fixwitness(meta, fix, expected=False)
            proof_e = fixwitness(meta, fix, expected=True) if meta.get("incident") else proof
            rows.append({
                "case": meta["id"], "kind": meta["kind"], "fix": fix.name, "source": source,
                "label": label, "pattern": pattern,
                "job runs": runs, "sample test": same,
                "fixwitness": proof["verdict"] == "PASS", "fixwitness+exp": proof_e["verdict"] == "PASS",
                "score": proof["confidence"]["score"], "score+exp": proof_e["confidence"]["score"],
                "baseline_reason": why,
                "fixwitness_reason": "; ".join(proof["reasons"]),
                "fixwitness+exp_reason": "; ".join(proof_e["reasons"]),
            })
            mark = "ok" if (rows[-1]["fixwitness+exp"] == (label == "correct")) or label == "unknown" else "MISS"
            mark = mark if source == "benchmark" else "agent"
            print(f"{meta['id']:28} {fix.name:28} {label:8} runs={int(runs)} sample={int(same)} "
                  f"fw={proof['verdict']:12} fw+exp={proof_e['verdict']:12} {mark}", flush=True)
    return rows


def summarise(rows: list[dict], seconds: float) -> str:
    labelled = [r for r in rows if r["source"] == "benchmark" and r["label"] in ("correct", "wrong")]
    wrong = [r for r in labelled if r["label"] == "wrong"]
    right = [r for r in labelled if r["label"] == "correct"]

    def caught(rs, m):
        return sum(1 for r in rs if not r[m])

    def pct(a, b):
        return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "0/0"

    out = [f"# fixwitness benchmark results", "",
           f"fixwitness {__version__} · {len(rows)} fixes across {len({r['case'] for r in rows})} cases "
           f"({len(right)} correct, {len(wrong)} wrong, plus {len(rows) - len(labelled)} assistant fixes) · "
           f"run time {seconds:.0f}s", "",
           "The wrong fixes are **synthetic**. Each models a documented failure pattern (named per fix below); "
           "none were produced by an AI agent. Fixes written by AI assistants are listed separately at the end.", "",
           "## Headline", "",
           "| Check | Wrong fixes caught | Correct fixes wrongly rejected |", "|---|---|---|"]
    for m in METHODS:
        out.append(f"| {m} | {pct(caught(wrong, m), len(wrong))} | {pct(caught(right, m), len(right))} |")
    out += ["", "`fixwitness+exp` gives fixwitness the correct output for the incident input; it differs from "
            "`fixwitness` only for incident cases.", "", "## By kind", "",
            "| Kind | Wrong fixes | Caught by: job runs | sample test | fixwitness | fixwitness+exp |",
            "|---|---|---|---|---|---|"]
    for kind in ("security", "incident", "refactor"):
        ws = [r for r in wrong if r["kind"] == kind]
        out.append(f"| {kind} | {len(ws)} | " + " | ".join(str(caught(ws, m)) for m in METHODS) + " |")

    misses = [r for r in wrong if r["fixwitness"]]
    alarms = [r for r in right if not r["fixwitness"]]
    out += ["", "## Where fixwitness is blind", ""]
    if misses:
        out.append("Wrong fixes that plain fixwitness accepted (no expected output):")
        out.append("")
        for r in misses:
            note = "caught when the expected output is given" if not r["fixwitness+exp"] else "not caught"
            out.append(f"- `{r['case']}/{r['fix']}`: {r['pattern']}. {note}.")
    else:
        out.append("No wrong fix was accepted.")
    out += ["", "False alarms on correct fixes:", ""]
    out += [f"- `{r['case']}/{r['fix']}`: {r['fixwitness_reason']}" for r in alarms] or ["- none"]

    out += ["", "## Every fix", "", "| Case | Fix | Label | Failure pattern | Job runs | Sample test | fixwitness | +exp | Score |",
            "|---|---|---|---|---|---|---|---|---|"]
    yes = {True: "accept", False: "**reject**"}
    for r in (r for r in rows if r["source"] == "benchmark"):
        out.append(f"| {r['case']} | {r['fix']} | {r['label']} | {r['pattern']} | {yes[r['job runs']]} | "
                   f"{yes[r['sample test']]} | {yes[r['fixwitness']]} | {yes[r['fixwitness+exp']]} | {r['score+exp']} |")
    agent_rows = [r for r in rows if r["source"].startswith("agent:")]
    if agent_rows:
        out += ["", "## Assistant fixes", "",
                "Labels come from `study/labels.csv` (code review; see `study/README.md`). They are not used in the "
                "headline above.", "",
                "| Agent | Case | Label | Job runs | Sample test | fixwitness | +exp | Score | Reason |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r in agent_rows:
            out.append(f"| {r['source'][6:]} | {r['case']} | {r['label']} | {yes[r['job runs']]} | "
                       f"{yes[r['sample test']]} | {yes[r['fixwitness']]} | {yes[r['fixwitness+exp']]} | "
                       f"{r['score+exp']} | {r['fixwitness+exp_reason'] or '-'} |")
    return "\n".join(out) + "\n"


def write_prompts() -> None:
    for case_dir in sorted(p for p in CASES.iterdir() if p.is_dir()):
        meta = load_case(case_dir)
        code = (case_dir / meta["script"]).read_text(encoding="utf-8")
        lang = "bash" if meta["script"].endswith(".sh") else "python"
        parts = [f"# {meta['id']}: {meta['title']}", "", meta["task"], "",
                 f"Files: `{meta['script']}` (below) and `sample.csv` (normal data)"
                 + (f", `{meta['incident']}` (the input that broke the job)" if meta.get("incident") else "") + ".",
                 f"The job is run as: `{meta['run']}`", "",
                 "Reply with the complete fixed file only.", "", f"```{lang}", code.rstrip(), "```", ""]
        (case_dir / "PROMPT.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote PROMPT.md in {len(list(CASES.iterdir()))} cases")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "prompts":
        write_prompts()
        return 0
    start = time.time()
    rows = run_all()
    with open(HERE / "results.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (HERE / "RESULTS.md").write_text(summarise(rows, time.time() - start), encoding="utf-8")
    print(f"\nwrote {HERE / 'results.csv'} and {HERE / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
