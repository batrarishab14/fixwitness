"""Run fixwitness on the frozen candidates of the real-repository study (see PROTOCOL.md).

    python benchmark/realrepo/run_study.py --shard 3 --shards 20 --clones DIR --out DIR

For each candidate in this shard: check out the commit in a full clone of its package and run
`fixwitness check --base <parent> --no-attacks` there, exactly as a user would, with a time limit.
Writes one row per candidate to OUT/results_<shard>.csv and keeps summary.json and report.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ["id", "set", "label", "package", "release", "commit", "parent", "outcome", "verdicts", "differences",
          "categories", "first_finding", "seconds", "detail", "seeds_restored"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def in_scope(row: dict, every: bool) -> bool:
    return every or row["label"] in ("wrong-data", "crash-on-data", "refactor")


def clone(clones: Path, package: str) -> Path:
    repo = clones / package
    if not repo.is_dir():
        subprocess.run(["git", "clone", "--quiet", f"https://github.com/fivetran/{package}.git", str(repo)], check=True)
    return repo


def outcome(summary: dict | None, code: int) -> tuple[str, list[str]]:
    if summary is None:
        return ("not checked", [])
    verdicts = [c.get("verdict") for c in summary.get("checks", [])]
    if any(v == "FAIL" for v in verdicts):
        return ("FAIL", verdicts)
    if verdicts and all(v == "PASS" for v in verdicts):
        return ("PASS", verdicts)
    return ("not checked", verdicts)


def _memory_cap(gb: float):
    """A child's address-space limit, so a candidate that runs out of memory fails on its own
    (recorded as "could not run") instead of filling the runner and ending the whole shard."""
    if gb <= 0:
        return None
    import resource
    cap = int(gb * 2**30)
    return lambda: resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def run_one(row: dict, clones: Path, out: Path, limit: int, warehouse: str | None = None,
            memory_gb: float = 0) -> dict:
    res = {k: row.get(k, "") for k in ("id", "set", "label", "package", "release", "commit", "parent")}
    dest = out / "runs" / row["id"].replace("/", "_")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    start = time.time()
    # Bug fixes are run in the direction a bug arrives: the fixed commit is the original and the
    # parent (which has the bug) is the change, so the question is whether fixwitness flags the
    # change that introduces the bug (PROTOCOL.md, amendment "direction"). Refactors: parent ->
    # commit.
    bug = row["set"] == "bug"
    base, head = (row["commit"], row["parent"]) if bug else (row["parent"], row["commit"])
    try:
        repo = clone(clones, row["package"])
        git(repo, "checkout", "-q", "-f", head)
        git(repo, "clean", "-qfdx")
        # The sample is the data the original had: seed files the commit changed are put back as
        # they were, and seed files it added are removed (PROTOCOL.md, amendment "seeds").
        restored = 0
        if not bug:  # bug fixes: the working tree is the parent already, with the parent's data
            changed = [l.split("\t") for l in git(repo, "diff", "--name-status", "--no-renames", row["parent"],
                                                     row["commit"], "--", "*.csv").splitlines() if l.strip()]
            for status, path in ((c[0], c[-1]) for c in changed):
                if status.startswith("A"):
                    (repo / path).unlink(missing_ok=True)
                else:
                    git(repo, "checkout", "-q", row["parent"], "--", path)
                restored += 1
        res["seeds_restored"] = restored
    except subprocess.CalledProcessError as exc:
        return {**res, "outcome": "not checked", "detail": f"checkout failed: {exc.stderr.strip()[:200]}",
                "seconds": round(time.time() - start)}
    cmd = [sys.executable, "-m", "fixwitness", "check", "--base", base, "--no-attacks",
           "--out-dir", str(dest / "out")] + (["--warehouse", warehouse] if warehouse else [])
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=limit,
                              preexec_fn=_memory_cap(memory_gb))
        code, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        code, log = -1, f"timed out after {limit}s\n" + ((exc.stdout or b"").decode(errors="replace")
                                                       if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    (dest / "log.txt").write_text(log, encoding="utf-8")
    summary_path = dest / "out" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
    kind, verdicts = outcome(summary, code)
    diffs, cats, first, detail = 0, set(), "", ""
    for c in (summary or {}).get("checks", []):
        proof_path = c.get("proof")
        if c.get("reason"):
            detail = (detail + " | " if detail else "") + str(c["reason"])[:300]
        if c.get("detail"):
            (dest / "error.txt").write_text(str(c["detail"]), encoding="utf-8")
        if proof_path and Path(proof_path).is_file():
            proof = json.loads(Path(proof_path).read_text(encoding="utf-8"))
            for d in proof.get("differences", []):
                diffs += 1
                cats.add(d.get("category", ""))
                if not first and d.get("kind") == "valid":
                    first = d.get("explanation") or "; ".join(d.get("details", [])[:2])
            if not detail and proof.get("verdict") != "PASS":
                detail = "; ".join(proof.get("reasons", []))[:300]
    if summary is None:
        detail = (log.strip().splitlines() or ["no output"])[-1][:300]
        if memory_gb > 0 and ("MemoryError" in log or "Cannot allocate memory" in log
                              or "std::bad_alloc" in log or "Out of Memory" in log):
            kind, detail = "not checked", f"could not run: out of memory (limit {memory_gb:g} GB)"
    return {**res, "outcome": kind, "verdicts": " ".join(v or "?" for v in verdicts), "differences": diffs,
            "categories": " ".join(sorted(cats)), "first_finding": first[:400], "detail": detail,
            "seconds": round(time.time() - start)}


def run_issue(name: str, clones: Path, out: Path) -> dict:
    """An open bug report: the fix in open_issues/NAME/fix.patch, and the evidence steps in issue.json."""
    import re
    folder = HERE / "open_issues" / name
    meta = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    repo = clone(clones, meta["package"])
    dest = out / "issues" / name
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "profiles").mkdir(parents=True)
    db = dest / "dbt.duckdb"
    (dest / "profiles" / "profiles.yml").write_text(
        f"{meta['profile']}:\n  target: dev\n  outputs:\n    dev:\n      type: duckdb\n      path: {json.dumps(str(db))}\n"
        f"      schema: {json.dumps(meta['schema'])}\n      threads: 1\n", encoding="utf-8")
    env = dict(os.environ, DBT_PROFILES_DIR=str(dest / "profiles"), DBT_SEND_ANONYMOUS_USAGE_STATS="false")
    steps = []
    for i, step in enumerate(meta["steps"], 1):
        git(repo, "checkout", "-q", "-f", meta["base"])
        git(repo, "clean", "-qfdx")
        db.unlink(missing_ok=True)
        cmd = step["run"].replace("{patch}", str((folder / "fix.patch").resolve())).replace("{out}", str(dest))
        start = time.time()
        try:
            proc = subprocess.run(cmd, shell=True, cwd=repo, env=env, capture_output=True, text=True, timeout=1800)
            code, log = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            code, log = -1, "timed out"
        (dest / f"step{i}.log").write_text(f"$ {cmd}\n\n{log}", encoding="utf-8")
        got = {"name": step["name"], "expect": step["expect"], "exit": code, "seconds": round(time.time() - start)}
        if step["expect"] == "fixwitness":
            summary = next(iter(sorted(dest.glob("fw_*/summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)), None)
            data = json.loads(summary.read_text(encoding="utf-8")) if summary else {}
            got["verdict"] = data.get("verdict", "not checked")
            got["checks"] = [{k: c.get(k) for k in ("target", "kind", "verdict", "reason", "proof")}
                             for c in data.get("checks", [])]
            for c in data.get("checks", []):
                if c.get("proof") and Path(c["proof"]).is_file():
                    proof = json.loads(Path(c["proof"]).read_text(encoding="utf-8"))
                    b = proof.get("behavior", {})
                    c_ = next(x for x in got["checks"] if x["proof"] == c["proof"])
                    c_["cases"] = b.get("valid_inputs")
                    c_["identical"] = b.get("identical")
                    c_["changed"] = b.get("changed")
                    c_["expected_change"] = b.get("expected_change")
                    c_["expected_examples"] = [e.get("details", [])[:3] for e in (proof.get("expected_changes") or [])[:3]]
                    c_["findings"] = [d.get("explanation") for d in proof.get("differences", [])[:8]]
            got["ok"] = summary is not None
        else:
            want = re.compile(step["expect_log"]) if step.get("expect_log") else None
            got["ok"] = (code == 0) if step["expect"] == "pass" else (code != 0 and (want is None or bool(want.search(log))))
        steps.append(got)
        print(f"open:{name} step {i} {'ok ' if got['ok'] else 'NOT'} exit={code} {got.get('verdict', '')} "
              f"{got['seconds']}s  {step['name']}", flush=True)
    result = {"issue": meta["issue"], "title": meta["title"], "base": meta["base"], "steps": steps}
    (dest / "evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--clones", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="", help="comma-separated candidate ids")
    ap.add_argument("--all", action="store_true", help="also run the out-of-scope candidates")
    ap.add_argument("--limit", type=int, default=1500, help="seconds per candidate")
    ap.add_argument("--warehouse", default=os.environ.get("FIXWITNESS_STUDY_WAREHOUSE"),
                    help="compile and run in this warehouse (postgres://...) instead of DuckDB")
    ap.add_argument("--memory-gb", type=float, default=8,
                    help="address-space limit for each candidate's fixwitness run, in GB (0: none)")
    args = ap.parse_args()
    args.clones, args.out = args.clones.resolve(), args.out.resolve()  # fixwitness runs inside each clone
    rows = list(csv.DictReader((HERE / "candidates.csv").open(encoding="utf-8")))
    only = {x for x in args.only.split(",") if x}
    # Real fixes found after the list was frozen: run only when named, and reported apart.
    extra = list(csv.DictReader((HERE / "after_freeze.csv").open(encoding="utf-8")))
    rows += [r for r in extra if r["id"] in only]
    issues = sorted(x[5:] for x in only if x.startswith("open:"))
    rows = [r for r in rows if r["id"] in only] if only else [r for r in rows if in_scope(r, args.all)]
    mine = [r for i, r in enumerate(rows) if i % args.shards == args.shard]
    args.clones.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(issues):
        if i % args.shards == args.shard:
            run_issue(name, args.clones, args.out)
    path = args.out / f"results_{args.shard:02d}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in mine:
            res = run_one(r, args.clones, args.out, args.limit, args.warehouse, args.memory_gb)
            w.writerow(res)
            fh.flush()
            print(f"{res['id']:40} {res['set']:9} {res['outcome']:12} {res.get('differences', '')!s:>4} "
                  f"{res['seconds']:>5}s  {res.get('detail', '')[:120]}", flush=True)


if __name__ == "__main__":
    main()
