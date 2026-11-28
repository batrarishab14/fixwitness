"""Migration benchmark: pandas -> Polars rewrites, correct and with typical migration mistakes.

Each task is a small pandas script (CSV in, CSV out) and its Polars migration. Every task has one correct
migration and one or more wrong ones, each modelling a documented pandas/Polars difference (null group keys,
default quantile interpolation, null ordering, ddof, integer division ...). Written by the author, not found
in the wild, and small: read RESULTS.md for what that means.

Ground truth is measured, not asserted: a migration is "really different" if its output differs from the
original on a large realistic dataset (3000 rows with NULL keys/amounts, ties, padded and mixed-case text).
The correct migrations must be identical there (the run stops if one is not).

Three ways to accept a migration are compared:
  sample test  the output on the small sample equals the original's
  fixwitness   `fixwitness check` on the same sample (verdict PASS)
  (neither needs an expected output)

Usage:  python3 benchmark/migration/run_migration_bench.py [--workers 3] [--only T1,T2]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

HEAD_PD = "import sys\nimport pandas as pd\ndf = pd.read_csv(sys.argv[1])\n"
# The Polars side pins what pandas infers (numeric columns) and what pandas reads as missing, as a careful
# migration does. An unpinned pl.read_csv differs on header-only files, "+7", "2_500" and "NA" (see RESULTS.md).
HEAD_PL = ("import sys\nimport polars as pl\n"
           "df = pl.read_csv(sys.argv[1], schema_overrides={'id': pl.Int64, 'amount': pl.Float64, 'rate': pl.Float64},\n"
           "                 null_values=['', 'NA', 'N/A', 'NULL', 'null', 'NaN', 'nan', 'None', 'n/a', '#N/A'])\n")
# Text-format edge cases (the number 2_500, shell characters ...) that a user migrating to Polars may decide not to care about.
TUNED_REVIEW = "numeric-format,delimiter-mix,shell-metachar,csv-structure,unicode,long,punctuation,quotes"

# task -> (original pandas body, {variant name: (is_correct, what it models, polars body)})
TASKS = {
 "T1-customer-revenue": (
  "paid = df[df.status == 'paid']\n"
  "out = paid.groupby('cust').agg(total=('amount', 'sum'), n=('amount', 'count')).reset_index().sort_values('cust')\n"
  "out.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "drops the null customer like groupby does",
     "out = df.filter(pl.col('status') == 'paid').drop_nulls('cust').group_by('cust').agg(total=pl.col('amount').sum(), n=pl.col('amount').count()).sort('cust')\nout.write_csv(sys.argv[2])\n"),
   "keeps_null_group": (False, "group_by keeps the NULL customer as a group; groupby dropped it",
     "out = df.filter(pl.col('status') == 'paid').group_by('cust').agg(total=pl.col('amount').sum(), n=pl.col('amount').count()).sort('cust')\nout.write_csv(sys.argv[2])\n"),
   "len_not_count": (False, "pl.len() counts rows, count() counted non-null amounts",
     "out = df.filter(pl.col('status') == 'paid').drop_nulls('cust').group_by('cust').agg(total=pl.col('amount').sum(), n=pl.len()).sort('cust')\nout.write_csv(sys.argv[2])\n")}),
 "T2-percentiles": (
  "g = df.groupby('status')['amount']\n"
  "out = pd.DataFrame({'p90': g.quantile(0.9), 'median': g.median()}).reset_index().sort_values('status')\n"
  "out.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "quantile with linear interpolation",
     "out = df.drop_nulls('status').group_by('status').agg(p90=pl.col('amount').quantile(0.9, 'linear'), median=pl.col('amount').median()).sort('status')\nout.write_csv(sys.argv[2])\n"),
   "default_quantile": (False, "Polars quantile defaults to nearest, pandas to linear",
     "out = df.drop_nulls('status').group_by('status').agg(p90=pl.col('amount').quantile(0.9), median=pl.col('amount').median()).sort('status')\nout.write_csv(sys.argv[2])\n")}),
 "T3-top-orders": (
  "out = df.sort_values(['amount', 'id']).head(5)[['id', 'amount']]\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "nulls last, like pandas",
     "out = df.sort(['amount', 'id'], nulls_last=True).head(5).select('id', 'amount')\nout.write_csv(sys.argv[2])\n"),
   "nulls_first": (False, "Polars sorts NULL first by default, pandas last",
     "out = df.sort(['amount', 'id']).head(5).select('id', 'amount')\nout.write_csv(sys.argv[2])\n")}),
 "T4-spread": (
  "out = df.groupby('status')['amount'].agg(['mean', 'std']).reset_index().sort_values('status')\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "sample standard deviation (ddof=1)",
     "out = df.drop_nulls('status').group_by('status').agg(mean=pl.col('amount').mean(), std=pl.col('amount').std()).sort('status')\nout.write_csv(sys.argv[2])\n"),
   "population_std": (False, "ddof=0 (numpy habit) instead of the sample deviation",
     "out = df.drop_nulls('status').group_by('status').agg(mean=pl.col('amount').mean(), std=pl.col('amount').std(ddof=0)).sort('status')\nout.write_csv(sys.argv[2])\n")}),
 "T5-ratio": (
  "df['ratio'] = df['amount'] / df['rate']\n"
  "out = df.groupby('cust')['ratio'].mean().reset_index().sort_values('cust')\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "true division",
     "out = df.drop_nulls('cust').with_columns(ratio=pl.col('amount') / pl.col('rate')).group_by('cust').agg(ratio=pl.col('ratio').mean()).sort('cust')\nout.write_csv(sys.argv[2])\n"),
   "floor_division": (False, "// truncates where / did not",
     "out = df.drop_nulls('cust').with_columns(ratio=pl.col('amount') // pl.col('rate')).group_by('cust').agg(ratio=pl.col('ratio').mean()).sort('cust')\nout.write_csv(sys.argv[2])\n")}),
 "T6-fill-missing": (
  "df['amount'] = df['amount'].fillna(0)\n"
  "out = df.groupby('status')['amount'].mean().reset_index().sort_values('status')\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "fill_null(0) kept",
     "out = df.with_columns(pl.col('amount').fill_null(0)).drop_nulls('status').group_by('status').agg(amount=pl.col('amount').mean()).sort('status')\nout.write_csv(sys.argv[2])\n"),
   "fill_dropped": (False, "the fillna step was lost in the migration",
     "out = df.drop_nulls('status').group_by('status').agg(amount=pl.col('amount').mean()).sort('status')\nout.write_csv(sys.argv[2])\n")}),
 "T7-first-per-group": (
  "out = df.sort_values('id').drop_duplicates(subset=['cust', 'status'], keep='first')[['cust', 'status', 'id']].sort_values(['cust', 'status'])\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "keep the first row of each group, ordered by id",
     "out = df.sort('id').unique(subset=['cust', 'status'], keep='first', maintain_order=True).select('cust', 'status', 'id').sort(['cust', 'status'], nulls_last=True)\nout.write_csv(sys.argv[2])\n"),
   "keeps_last": (False, "keep='last' instead of the first row",
     "out = df.sort('id').unique(subset=['cust', 'status'], keep='last', maintain_order=True).select('cust', 'status', 'id').sort(['cust', 'status'], nulls_last=True)\nout.write_csv(sys.argv[2])\n")}),
 "T8-clean-text": (
  "df['status'] = df['status'].str.strip().str.lower()\n"
  "out = df.groupby('status').size().reset_index(name='n').sort_values('status')\nout.to_csv(sys.argv[2], index=False)\n",
  {"correct": (True, "strip and lower",
     "out = df.drop_nulls('status').with_columns(pl.col('status').str.strip_chars().str.to_lowercase()).group_by('status').agg(n=pl.len()).sort('status')\nout.write_csv(sys.argv[2])\n"),
   "strip_dropped": (False, "the strip was lost in the migration",
     "out = df.drop_nulls('status').with_columns(pl.col('status').str.to_lowercase()).group_by('status').agg(n=pl.len()).sort('status')\nout.write_csv(sys.argv[2])\n")}),
}


def make_data(rows: int, seed: int) -> str:
    """Realistic orders: NULL customers and amounts, ties, padded and mixed-case status."""
    rnd = random.Random(seed)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["id", "cust", "status", "amount", "rate"])
    for i in range(1, rows + 1):
        cust = "" if rnd.random() < 0.05 else rnd.choice("abcdefghij")
        status = rnd.choice(["paid"] * 6 + ["refunded", "Paid", " paid", "PAID ", "pending"])
        amount = "" if rnd.random() < 0.08 else rnd.choice([round(rnd.uniform(0, 500), 2), rnd.choice([10, 20, 20, 50])])
        w.writerow([i, cust, status, amount, rnd.choice([0.5, 1, 1.5, 2, 3, 4])])
    return out.getvalue()


def run(script: Path, data: Path, out: Path) -> str | None:
    p = subprocess.run([sys.executable, str(script), str(data), str(out)], capture_output=True, text=True, timeout=300)
    return None if p.returncode == 0 and out.exists() else (p.stderr.strip().splitlines() or ["failed"])[-1]


def same(a: Path, b: Path) -> bool:
    import pandas as pd
    try:
        x, y = pd.read_csv(a), pd.read_csv(b)
        if list(x.columns) != list(y.columns) or len(x) != len(y):
            return False
        pd.testing.assert_frame_equal(x, y, check_dtype=False, rtol=1e-9, atol=1e-12)
        return True
    except Exception:
        return False


def fixwitness(before: Path, after: Path, sample: Path, work: Path, review: str = "") -> dict:
    t = time.time()
    p = subprocess.run([sys.executable, "-m", "fixwitness", "check", "--before", str(before), "--after", str(after),
                        "--sample", str(sample), "--no-attacks", "--out-dir", str(work / "out")]
                       + (["--review", review] if review else []),
                       capture_output=True, text=True, timeout=1500)
    proof = work / "out" / "proof.json"
    d = json.loads(proof.read_text()) if proof.exists() else {}
    b = d.get("behavior", {})
    return {"verdict": d.get("verdict", "ERROR"), "changed": b.get("changed"), "identical": b.get("identical"),
            "seconds": round(time.time() - t), "error": "" if d else p.stderr.strip()[-200:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--sample-rows", type=int, default=20)
    args = ap.parse_args()
    only = {x for x in args.only.split(",") if x}
    root = Path(tempfile.mkdtemp(prefix="fw-migration-"))
    big = root / "big.csv"
    big.write_text(make_data(3000, 7))
    sample = root / "sample.csv"
    lines = make_data(3000, 7).splitlines()
    sample.write_text("\n".join(lines[: args.sample_rows + 1]) + "\n")
    rows, jobs = [], []
    for task, (orig_body, variants) in TASKS.items():
        if only and not any(task.startswith(o) for o in only):
            continue
        d = root / task
        d.mkdir()
        (d / "original.py").write_text(HEAD_PD + orig_body)
        for name, (correct, models, body) in variants.items():
            (d / f"{name}.py").write_text(HEAD_PL + body)
            jobs.append((task, name, correct, models, d))
    # ground truth on the large dataset
    for task, name, correct, models, d in jobs:
        o, v = d / "o_big.csv", d / f"{name}_big.csv"
        e1, e2 = run(d / "original.py", big, o), run(d / f"{name}.py", big, v)
        if e1 or e2:
            raise SystemExit(f"{task}/{name}: a script failed on the large data: {e1 or e2}")
        really = not same(o, v)
        if correct and really:
            raise SystemExit(f"{task}/{name} is labelled correct but differs on the large data: fix the benchmark")
        d_so, d_sv = d / "o_s.csv", d / f"{name}_s.csv"
        s1, s2 = run(d / "original.py", sample, d_so), run(d / f"{name}.py", sample, d_sv)
        rows.append({"task": task, "variant": name, "correct": correct, "models": models,
                     "really_different": really, "sample_test_catches": bool(s1 is None and s2 is None and not same(d_so, d_sv)) or bool(s2),
                     "dir": d})

    def check(r):
        a, b = r["dir"] / "original.py", r["dir"] / f"{r['variant']}.py"
        res = fixwitness(a, b, sample, r["dir"] / f"w_{r['variant']}")
        tuned = fixwitness(a, b, sample, r["dir"] / f"t_{r['variant']}", TUNED_REVIEW)
        return {**r, **res, "verdict_tuned": tuned["verdict"], "changed_tuned": tuned["changed"]}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(check, rows))
    for r in results:
        r["fixwitness_catches"] = r["verdict"] == "FAIL"
        r["tuned_catches"] = r["verdict_tuned"] == "FAIL"
        r.pop("dir")
    out = HERE / "results.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(results)
    wrong = [r for r in results if r["really_different"]]
    right = [r for r in results if r["correct"]]
    print(f"{'task':22} {'variant':18} correct really_diff sample_test default tuned")
    for r in results:
        print(f"{r['task']:22} {r['variant']:18} {r['correct']!s:7} {r['really_different']!s:11} {r['sample_test_catches']!s:11} {r['verdict']:8} {r['verdict_tuned']}")
    print(f"\nreally different migrations: {len(wrong)}; caught by sample test {sum(r['sample_test_catches'] for r in wrong)}, "
          f"by fixwitness default {sum(r['fixwitness_catches'] for r in wrong)}, tuned {sum(r['tuned_catches'] for r in wrong)}")
    print(f"correct migrations: {len(right)}; false alarms: default {sum(r['fixwitness_catches'] for r in right)}, "
          f"tuned {sum(r['tuned_catches'] for r in right)}; verdicts default {sorted({r['verdict'] for r in right})}, tuned {sorted({r['verdict_tuned'] for r in right})}")
    print(f"sample: {args.sample_rows} rows; NULL cust {sum(1 for l in lines[1:args.sample_rows+1] if l.split(',')[1]=='')}, "
          f"NULL amount {sum(1 for l in lines[1:args.sample_rows+1] if l.split(',')[3]=='')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
