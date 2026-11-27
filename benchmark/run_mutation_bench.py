"""fixwitness mutation benchmark: does it catch a SQL change nobody designed on purpose?

Unlike benchmark/run_sql_bench.py, the wrong versions here are not written by hand. They are
produced mechanically: standard SQL mutation operators (join type, comparison, AND/OR, aggregate,
NULL tests, DISTINCT, UNION, NOT, numeric literals) are applied one at a time to each original
query under benchmark/sql/. Each mutant is a "refactor" that must not change the result.

Ground truth is independent of fixwitness: a mutant is *non-equivalent* when its output differs
from the original's on the case's sample tables or on any of N seeded random tables built from
the sample's own values (plus NULLs and perturbed numbers). A mutant that never differs on those
tables is *likely equivalent*; the random search cannot prove equivalence, so those are reported
separately and never counted as misses or false alarms without a hand review.

Usage:
  python3 benchmark/run_mutation_bench.py [--engine sqlite|duckdb|auto] [--trials 40] [--limit N]
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import re
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from run_sql_bench import CASES, baseline, fixwitness  # noqa: E402
from fixwitness import __version__  # noqa: E402
from fixwitness.compare import CompareOptions, compare  # noqa: E402
from fixwitness.sql import choose_engine, make_bundle, run_query, table_types  # noqa: E402

OUT = HERE / "mutation"  # not under sql/: run_sql_bench treats every folder there as a case

# (name, regex, replacement) -- replacement may be a callable(match) -> str
OPERATORS = [
    ("inner join -> left join", r"\binner\s+join\b", "left join"),
    ("join -> left join", r"(?<!left )(?<!inner )(?<!outer )\bjoin\b", "left join"),
    ("left join -> inner join", r"\bleft\s+join\b", "join"),
    ("= -> <>", r"(?<![<>!=])=(?![=>])", "<>"),
    (">= -> >", r">=", ">"),
    ("<= -> <", r"<=", "<"),
    ("> -> >=", r"(?<![<>=-])>(?![=>])", ">="),
    ("< -> <=", r"<(?![=>])", "<="),
    ("AND -> OR", r"\band\b", "or"),
    ("OR -> AND", r"\bor\b", "and"),
    ("SUM -> AVG", r"\bsum\(", "avg("),
    ("AVG -> SUM", r"\bavg\(", "sum("),
    ("MAX -> MIN", r"\bmax\(", "min("),
    ("MIN -> MAX", r"\bmin\(", "max("),
    ("COUNT(x) -> COUNT(DISTINCT x)", r"\bcount\((?!\*|distinct)", "count(distinct "),
    ("IS NOT NULL -> IS NULL", r"\bis\s+not\s+null\b", "is null"),
    ("IS NULL -> IS NOT NULL", r"\bis\s+null\b(?!\s*\))", "is not null"),
    ("UNION ALL -> UNION", r"\bunion\s+all\b", "union"),
    ("UNION -> UNION ALL", r"\bunion\b(?!\s+all)", "union all"),
    ("add DISTINCT", r"\bselect\b(?!\s+distinct)", "select distinct"),
    ("drop DISTINCT", r"\bdistinct\s+", ""),
    ("drop NOT", r"\bnot\s+", ""),
    ("literal + 1", r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", lambda m: str(float(m.group()) + 1).rstrip("0").rstrip(".")),
]


def string_spans(sql: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"'(?:[^']|'')*'", sql)]


def mutants(sql: str) -> list[tuple[str, str]]:
    spans = string_spans(sql)
    seen, out = {sql}, []
    for name, pat, rep in OPERATORS:
        for m in re.finditer(pat, sql, flags=re.I):
            if any(s <= m.start() < e for s, e in spans):
                continue
            new = sql[:m.start()] + (rep(m) if callable(rep) else rep) + sql[m.end():]
            new = re.sub(r"[ \t]{2,}", " ", new)
            if new not in seen:
                seen.add(new)
                out.append((name, new))
    return out


def read_csv(b: bytes) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(b.decode("utf-8"))))
    return rows[0], rows[1:]


def random_tables(tables: dict[str, bytes], rng: random.Random, n_rows: int = 12) -> dict[str, bytes]:
    out = {}
    for name, b in tables.items():
        header, rows = read_csv(b)
        cols = list(zip(*rows)) if rows else [() for _ in header]
        gen = []
        for _ in range(n_rows):
            row = []
            for vals in cols:
                r = rng.random()
                if r < 0.15:
                    row.append("")
                    continue
                v = rng.choice(vals) if vals else ""
                try:
                    f = float(v)
                    if v.lstrip("-").isdigit() and rng.random() < 0.15:  # orphan / unseen key or id
                        v = str(rng.randint(0, int(max(abs(float(x)) for x in vals if x.lstrip("-").replace(".", "", 1).isdigit()) * 2) + 2))
                    elif rng.random() < 0.3:
                        v = rng.choice(["0", "-5", str(round(f * rng.uniform(0.1, 3), 2)), str(f + 1)])
                except ValueError:
                    if rng.random() < 0.15:
                        v = v.upper() if rng.random() < 0.5 else v + " "
                row.append(v)
            gen.append(row)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(gen)
        out[name] = buf.getvalue().encode("utf-8")
    return out


def run(sql: str, tables: dict[str, bytes], types: dict, engine: str) -> bytes | None:
    try:
        return run_query(sql, make_bundle(tables, types), engine)
    except Exception:
        return None


def same(a: bytes | None, b: bytes | None) -> bool:
    if a is None or b is None:
        return a is b
    return compare(a, b, CompareOptions(mode="csv"))[0] != "changed"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="auto", choices=["auto", "duckdb", "sqlite"])
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0, help="max mutants per query (0 = all)")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    engine = choose_engine(a.engine)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.time()
    for case_dir in sorted(p for p in CASES.iterdir() if p.is_dir() and p.name != "mutation"):
        meta = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
        meta["dir"], meta["id"] = case_dir, case_dir.name
        meta.pop("incident_tables", None)
        meta.pop("expected", None)
        meta["kind"] = "refactor"
        original = (case_dir / "original.sql").read_text()
        tables = {n: (case_dir / f).read_bytes() for n, f in meta["tables"].items()}
        types = {n: table_types(b) for n, b in tables.items()}
        orig_sample = run(original, tables, types, engine)
        rng = random.Random(a.seed)
        trial_sets = [random_tables(tables, rng) for _ in range(a.trials)]
        orig_trials = [run(original, t, types, engine) for t in trial_sets]
        ms = mutants(original)
        if a.limit:
            ms = ms[:a.limit]
        mdir = OUT / case_dir.name
        mdir.mkdir(exist_ok=True)
        for i, (op, sql) in enumerate(ms):
            f = mdir / f"m{i:02d}.sql"
            f.write_text(sql, encoding="utf-8")
            sample_out = run(sql, tables, types, engine)
            if sample_out is None:
                rows.append({"case": meta["id"], "mutant": f.name, "operator": op, "truth": "invalid (does not run)",
                             "sample test": "", "fixwitness": ""})
                continue
            sample_diff = not same(orig_sample, sample_out)
            gt_diff = sample_diff or any(not same(o, run(sql, t, types, engine))
                                         for o, t in zip(orig_trials, trial_sets))
            proof = fixwitness(meta, f, engine, expected=False)
            rows.append({"case": meta["id"], "mutant": f.name, "operator": op,
                         "truth": "non-equivalent" if gt_diff else "likely equivalent",
                         "sample test": "caught" if sample_diff else "accepted",
                         "fixwitness": "caught" if proof["verdict"] != "PASS" else "accepted"})
            r = rows[-1]
            print(f"{meta['id']:28} {f.name} {op:30} {r['truth']:18} sample={r['sample test']:8} fw={r['fixwitness']}", flush=True)
    write(rows, engine, time.time() - t0, a)
    return 0


def write(rows: list[dict], engine: str, seconds: float, a) -> None:
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["case", "mutant", "operator", "truth", "sample test", "fixwitness"])
        w.writeheader()
        w.writerows(rows)
    ne = [r for r in rows if r["truth"] == "non-equivalent"]
    eq = [r for r in rows if r["truth"] == "likely equivalent"]
    inv = [r for r in rows if r["truth"].startswith("invalid")]

    def pct(n, d):
        return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"

    by_op: dict[str, list[dict]] = {}
    for r in ne:
        by_op.setdefault(r["operator"], []).append(r)
    md = ["# fixwitness mutation benchmark", "",
          f"fixwitness {__version__} · engine {engine} · {len(rows)} mutants from {len({r['case'] for r in rows})} queries · "
          f"{a.trials} random tables per query · seed {a.seed} · {seconds:.0f}s", "",
          "Mutants are generated mechanically, not designed by hand. **Non-equivalent** = output differs from the original on "
          "the sample or on any random table. **Likely equivalent** = no difference found; the search cannot prove equivalence, "
          "so these are not scored until reviewed by hand.", "",
          "| Group | Count |", "|---|---|",
          f"| non-equivalent | {len(ne)} |", f"| likely equivalent | {len(eq)} |", f"| invalid (does not run) | {len(inv)} |", "",
          "## Headline (non-equivalent mutants only)", "",
          "| Check | Mutants caught |", "|---|---|",
          f"| sample test (output on today's sample unchanged) | {pct(sum(r['sample test'] == 'caught' for r in ne), len(ne))} |",
          f"| fixwitness | {pct(sum(r['fixwitness'] == 'caught' for r in ne), len(ne))} |", "",
          "## Likely-equivalent mutants that fixwitness rejected (review by hand)", ""]
    flagged = [r for r in eq if r["fixwitness"] == "caught"]
    md += [f"{len(flagged)} of {len(eq)}." ] + [f"- {r['case']}/{r['mutant']}: {r['operator']}" for r in flagged]
    md += ["", "## By operator (non-equivalent)", "", "| Operator | fixwitness | sample test |", "|---|---|---|"]
    for op, rs in sorted(by_op.items()):
        md.append(f"| {op} | {pct(sum(x['fixwitness'] == 'caught' for x in rs), len(rs))} | "
                  f"{pct(sum(x['sample test'] == 'caught' for x in rs), len(rs))} |")
    md += ["", "## Missed by fixwitness (non-equivalent)", ""]
    md += [f"- {r['case']}/{r['mutant']}: {r['operator']}" for r in ne if r["fixwitness"] == "accepted"] or ["none"]
    md += ["", "## Threats to validity", "",
           "- Only the 6 hand-written originals in `benchmark/sql/` are mutated, so query style is the author's.",
           "- Ground truth is a random search with a fixed budget; some 'likely equivalent' mutants may truly differ.",
           "- Single-statement SQLite/DuckDB queries only; no dbt, no Jinja, no DataFrames."]
    (OUT / "RESULTS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'RESULTS.md'}")


if __name__ == "__main__":
    sys.exit(main())
