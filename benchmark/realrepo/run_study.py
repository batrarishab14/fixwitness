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
          "categories", "first_finding", "seconds", "detail"]


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


def run_one(row: dict, clones: Path, out: Path, limit: int) -> dict:
    res = {k: row.get(k, "") for k in ("id", "set", "label", "package", "release", "commit", "parent")}
    dest = out / "runs" / row["id"].replace("/", "_")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    start = time.time()
    try:
        repo = clone(clones, row["package"])
        git(repo, "checkout", "-q", "-f", row["commit"])
        git(repo, "clean", "-qfdx")
    except subprocess.CalledProcessError as exc:
        return {**res, "outcome": "not checked", "detail": f"checkout failed: {exc.stderr.strip()[:200]}",
                "seconds": round(time.time() - start)}
    cmd = [sys.executable, "-m", "fixwitness", "check", "--base", row["parent"], "--no-attacks",
           "--out-dir", str(dest / "out")]
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=limit)
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
    return {**res, "outcome": kind, "verdicts": " ".join(v or "?" for v in verdicts), "differences": diffs,
            "categories": " ".join(sorted(cats)), "first_finding": first[:400], "detail": detail,
            "seconds": round(time.time() - start)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--clones", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="", help="comma-separated candidate ids")
    ap.add_argument("--all", action="store_true", help="also run the out-of-scope candidates")
    ap.add_argument("--limit", type=int, default=1500, help="seconds per candidate")
    args = ap.parse_args()
    rows = list(csv.DictReader((HERE / "candidates.csv").open(encoding="utf-8")))
    only = {x for x in args.only.split(",") if x}
    rows = [r for r in rows if r["id"] in only] if only else [r for r in rows if in_scope(r, args.all)]
    mine = [r for i, r in enumerate(rows) if i % args.shards == args.shard]
    args.clones.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"results_{args.shard:02d}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in mine:
            res = run_one(r, args.clones, args.out, args.limit)
            w.writerow(res)
            fh.flush()
            print(f"{res['id']:40} {res['set']:9} {res['outcome']:12} {res.get('differences', '')!s:>4} "
                  f"{res['seconds']:>5}s  {res.get('detail', '')[:120]}", flush=True)


if __name__ == "__main__":
    main()
