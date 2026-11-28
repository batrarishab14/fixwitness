import csv, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import run
pkg, repo = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(str(Path(__file__).resolve().parents[1] / "runs/run5/results.csv"))) if r["package"] == pkg]
for r in rows:
    res = run(repo, r["commit"], r["parent"])
    f = [(x["kind"], x["name"]) for x in res.get("findings", [])]
    print(f'{r["id"]:28} {r["set"]:9} outcome={r["outcome"]:12} assessed={res.get("assessed")} lits={res.get("literals_checked")} cols={res.get("columns_checked")} findings={f}')
