"""Command-line interface: fixwitness check | init | replay | demo | categories | mcp."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fixwitness import __version__
from fixwitness.cases import CATEGORY_DESCRIPTIONS, DEFAULT_KIND, SampleError
from fixwitness.config import ConfigError, load_config
from fixwitness.core import dry_run, replay, run_check
from fixwitness.report import markdown, plan_text, write_outputs
from fixwitness.runner import RunConfigError

EXAMPLES = Path(__file__).parent / "examples"


def _csv_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _table_map(values: list[str] | None, flag: str) -> dict[str, str] | None:
    if not values:
        return None
    out = {}
    for item in values:
        name, sep, path = item.partition("=")
        if not sep or not name.strip() or not path.strip():
            raise ConfigError(f"{flag} expects NAME=FILE.csv, got {item!r}")
        out[name.strip()] = str((Path.cwd() / Path(path.strip()).expanduser()).resolve())
    return out


def _overrides(args: argparse.Namespace) -> dict:
    return {
        "tables": _table_map(args.table, "--table"),
        "incident_tables": _table_map(args.incident_table, "--incident-table"),
        "engine": args.engine, "sql_ordered": True if args.sql_ordered else None,
        "dialect": args.dialect, "sql_outputs": _csv_list(args.sql_outputs),
        "function": args.function, "library": args.library,
        "manifest": args.manifest, "base_manifest": args.base_manifest, "warehouse": args.warehouse,
        "path": args.path, "base": args.base, "command": args.command, "incident": args.incident,
        "incident_expected": args.incident_expected,
        "attacks": False if args.no_attacks else None,
        "before": args.before, "after": args.after, "sample": args.sample, "run": args.run,
        "run_after": args.run_after,
        "columns": _csv_list(args.columns), "review": _csv_list(args.review), "output": args.output,
        "ignore_columns": _csv_list(args.ignore_columns), "ignore_patterns": args.ignore_pattern or None,
        "expect_change": _csv_list(getattr(args, "expect_change", None)),
        "tolerance": args.tolerance, "unordered": True if args.unordered else None,
        "auto_ignore_unstable": False if args.no_auto_ignore else None,
        "shrink": False if getattr(args, "no_shrink", False) else None,
        "exercise_check": False if getattr(args, "no_exercise_check", False) else None,
        "strict_robustness": True if getattr(args, "strict_robustness", False) else None,
        "same_numbers": True if getattr(args, "same_numbers", False) else None,
        "max_cases": args.max_cases, "seed": args.seed, "timeout": args.timeout, "workers": args.workers,
        "pass_env": args.pass_env or None, "allow_any_command": True if args.allow_any_command else None,
        "no_network": True if args.no_network else None,
    }


def _config(args: argparse.Namespace):
    config_path = Path(args.config) if args.config else None
    explicit = args.path or args.before or args.command
    if config_path is None and not explicit and Path("fixwitness.toml").is_file():
        config_path = Path("fixwitness.toml")
    overrides = _overrides(args)
    if config_path is None and Path("fixwitness.toml").is_file():  # differences marked as intended still apply
        import tomllib
        try:
            with open("fixwitness.toml", "rb") as fh:
                overrides["accept"] = tomllib.load(fh).get("accept")
        except (OSError, tomllib.TOMLDecodeError):
            pass
    return load_config(config_path, overrides)


def _whole_change(cfg, args: argparse.Namespace) -> int | None:
    """Several checks for one change (the whole working tree, or a file with several changed
    functions); None when the change is a single ordinary check."""
    from fixwitness.changes import plan_items, run_items, summary_markdown
    whole = not (cfg.path or cfg.command or cfg.before or cfg.after or cfg.manifest)
    if not whole and not (cfg.path and not cfg.command and not cfg.function
                          and cfg.resolve(cfg.path).suffix == ".py"):
        return None
    try:
        items, skipped = plan_items(cfg)
    except Exception as exc:
        if whole:
            raise ConfigError(f"nothing to check: {exc}") from exc
        return None
    if not whole and len(items) == 1 and items[0].kind == "script":
        return None
    if not items:
        print("fixwitness: nothing to check in this change" + (
            ": " + "; ".join(f"{p} ({why})" for p, why in skipped) if skipped else ""))
        return 0 if whole else 1
    if args.dry_run:
        for it in items:
            print(f"  {it.kind:10} {it.target}")
        for p, why in skipped:
            print(f"  {'skipped':10} {p}: {why}")
        return 0
    out = Path(args.out_dir)
    result = run_items(cfg, items, out)
    text = summary_markdown(result, skipped)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(text, encoding="utf-8")
    _open(args, _write_whole_html(result, skipped, out, cfg))
    clean = {"verdict": result["verdict"], "checks": [{k: v for k, v in r.items() if not k.startswith("_")}
                                                       for r in result["checks"]],
             "not_checked": [{"path": p, "why": w} for p, w in skipped]}
    (out / "summary.json").write_text(json.dumps(clean, indent=2), encoding="utf-8")
    print(json.dumps(clean, indent=2) if args.json else text)
    return 0 if result["verdict"] == "PASS" else 1


def _open(args: argparse.Namespace, path: Path | None) -> None:
    if path is not None and getattr(args, "open", False):
        import webbrowser
        webbrowser.open(path.resolve().as_uri())
    elif path is not None and not getattr(args, "json", False):
        print(f"Report: {path}")


def _write_whole_html(result: dict, skipped, out: Path, cfg) -> Path | None:
    from fixwitness.core import REPRO
    from fixwitness.htmlreport import render
    checks = []
    for r in result["checks"]:
        proof = r.get("_proof")
        info = REPRO.get(proof["proof_id"], {}) if proof else {}
        checks.append({"target": r["target"], "kind": r["kind"], "verdict": r["verdict"], "proof": proof,
                       "reason": r.get("reason"), "explained": info.get("explained") or {},
                       "repro_dir": Path(r["proof"]).parent / "repro" if r.get("proof") else None})
    base = next((r["_proof"]["inputs"].get("base_commit") for r in result["checks"] if r.get("_proof")), None)
    context = (f"Original: {cfg.base}" + (f" (commit {base[:12]})" if base else "") + ". Fix: your working tree.")
    try:
        path = out / "report.html"
        path.write_text(render(checks, skipped, "fixwitness report", context), encoding="utf-8")
        return path
    except Exception as exc:
        print(f"fixwitness: report.html could not be built: {exc}", file=sys.stderr)
        return None


def cmd_check(args: argparse.Namespace) -> int:
    cfg = _config(args)
    multi = _whole_change(cfg, args)
    if multi is not None:
        return multi
    if args.dry_run:
        summary = dry_run(cfg)
        print(json.dumps(summary, indent=2) if args.json else plan_text(summary))
        return 0
    proof = run_check(cfg)
    proof_path = write_outputs(proof, Path(args.out_dir))
    print(json.dumps(proof, indent=2, ensure_ascii=False) if args.json else markdown(proof, str(proof_path)))
    _open(args, proof_path.parent / "report.html")
    if proof["verdict"] != "PASS":
        return 1
    if proof["confidence"]["score"] < args.min_confidence:
        print(f"Confidence {proof['confidence']['score']} is below --min-confidence {args.min_confidence}.")
        return 1
    return 0


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + " }"
    return json.dumps(str(v))


def cmd_accept(args: argparse.Namespace) -> int:
    from fixwitness.config import append_accept
    path = Path(args.config or "fixwitness.toml")
    entry = append_accept(path, args.target, args.category, args.column, args.note)
    print(f"Recorded in {path}: {entry}. Inputs of this kind are now reported as reviewed, not failed.")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    from fixwitness.plan import repo_root
    from fixwitness.setup import setup
    try:
        root = repo_root(Path.cwd())
    except Exception:
        root = Path.cwd()
    for line in setup(args.target, root, args.instructions):
        print(line)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from fixwitness.doctor import checks, render
    from fixwitness.plan import repo_root
    try:
        root = repo_root(Path.cwd())
    except Exception:
        root = Path.cwd()
    warehouse = args.warehouse or os.environ.get("FIXWITNESS_WAREHOUSE")
    text, ready = render(checks(root, args.base, warehouse, connect=bool(warehouse) and not args.no_connect))
    print(text, end="")
    return 0 if ready else 1


def cmd_ui(args: argparse.Namespace) -> int:
    from fixwitness.ui import serve
    return serve(port=args.port, open_browser=not args.no_browser)


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.write)
    if target.exists() and not args.force:
        print(f"fixwitness: {target} already exists (use --force to overwrite)", file=sys.stderr)
        return 2
    cfg = load_config(None, _overrides(args))
    summary = dry_run(cfg)
    here = Path.cwd()

    def rel(p: str | None) -> str | None:
        if not p:
            return None
        q = Path(p).resolve()
        try:
            return q.relative_to(here.resolve()).as_posix()
        except ValueError:
            return str(q)

    fix = {}
    if cfg.mode() == "files":
        fix["before"], fix["after"] = rel(str(cfg.resolve(cfg.before))), rel(str(cfg.resolve(cfg.after)))
    else:
        if cfg.path:
            fix["path"] = rel(str(cfg.resolve(cfg.path)))
        fix["base"] = cfg.base
        if cfg.command:
            fix["command"] = cfg.command
    if cfg.tables:
        fix["sample"] = None
    else:
        fix["sample"] = rel(summary["sample"])
    if cfg.incident:
        fix["incident"] = rel(str(cfg.resolve(cfg.incident)))
    if cfg.incident_expected:
        fix["incident_expected"] = rel(str(cfg.resolve(cfg.incident_expected)))
    if not cfg.command and not cfg.tables and summary["output"] and "fixwitness.sqlrun" not in summary["run"] \
            and "fixwitness.pyrun" not in summary["run"]:
        fix["run"] = summary["run"]
    cases = {"attacks": cfg.attacks, "columns": cfg.columns or [], "review": cfg.review,
             "max_cases": cfg.max_cases, "seed": cfg.seed}
    compare = {"output": summary["output"], "ignore_columns": cfg.ignore_columns,
               "ignore_patterns": cfg.ignore_patterns, "tolerance": cfg.tolerance, "unordered": cfg.unordered,
               "timeout_seconds": cfg.timeout}
    sections = [("fix", fix), ("cases", cases), ("compare", compare)]
    if "fixwitness.sqlrun" in summary["run"] or "fixwitness.pyrun" in summary["run"]:
        sql = {"engine": cfg.engine, "sql_ordered": cfg.sql_ordered}
        if cfg.dialect:
            sql["dialect"] = cfg.dialect
        if cfg.function:
            sql["function"] = cfg.function
            sql["library"] = cfg.library
            sql.pop("engine")
        if cfg.sql_outputs:
            sql["sql_outputs"] = cfg.sql_outputs
        if cfg.tables:
            sql["tables"] = {k: rel(v) for k, v in cfg.tables.items()}
        if cfg.incident_tables:
            sql["incident_tables"] = {k: rel(v) for k, v in cfg.incident_tables.items()}
        sections.append(("sql", sql))
    out = ["# Written by `fixwitness init`. Run `fixwitness check` in this folder.", ""]
    for name, section in sections:
        out.append(f"[{name}]")
        out += [f"{k} = {_toml_value(v)}" for k, v in section.items() if v is not None]
        out.append("")
    target.write_text("\n".join(out), encoding="utf-8")
    print(plan_text(summary))
    print(f"Wrote {target}. Run `fixwitness check` to compare.")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    proof = json.loads(Path(args.proof).read_text(encoding="utf-8"))
    result = replay(proof, allow_any_command=True if args.allow_any_command else None)
    if result["reproduced"]:
        print(f"REPRODUCED: proof {result['original_proof_id'][:16]} gives the same evidence "
              f"(verdict {result['verdict']}).")
        return 0
    print("NOT REPRODUCED:")
    for p in result["problems"]:
        print(f"- {p}")
    return 1


def _git(cwd: Path, *a: str) -> None:
    subprocess.run(["git", "-c", "user.name=fixwitness", "-c", "user.email=fixwitness@example.invalid", *a],
                   cwd=cwd, check=True, capture_output=True)


def cmd_demo(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="fixwitness-demo-") as tmp:
        work = Path(tmp) / "examples"
        shutil.copytree(EXAMPLES, work)
        runs = [
            ("python_eval", "clean_amounts_fix_naive.py", "Python ETL: eval() replaced with float()  (the obvious AI fix)"),
            ("python_eval", "clean_amounts_fix_safe.py", "Python ETL: eval() replaced with a literal parser"),
            ("shell_eval", "normalize_regions_fix_naive.sh", "Shell: 'eval echo $region' removed  (the obvious AI fix)"),
            ("shell_eval", "normalize_regions_fix_safe.sh", "Shell: eval removed, whitespace handling kept"),
            ("pipeline_repair", "load_payments_repair_naive.py",
             "Self-healing repair: strip every non-digit so '1,250.00' parses  (the obvious agent repair)"),
            ("pipeline_repair", "load_payments_repair_safe.py",
             "Self-healing repair: accept thousands separators, change nothing else"),
        ]
        for folder, after, title in runs:
            cfg = load_config(work / folder / "fixwitness.toml", {"after": str(work / folder / after)})
            print("=" * 78 + f"\n{title}\n" + "=" * 78)
            print(markdown(run_check(cfg)))
        print("Note: every naive fix gives identical output on the sample file itself, and the naive")
        print("repair makes the failing pipeline green. Only the generated inputs show what they break.\n")

        if shutil.which("git"):
            repo = Path(tmp) / "repo"
            (repo / "etl").mkdir(parents=True)
            shutil.copy(work / "python_eval" / "clean_amounts.py", repo / "etl" / "clean_amounts.py")
            shutil.copy(work / "python_eval" / "sample.csv", repo / "etl" / "sample.csv")
            _git(repo, "init", "-q")
            _git(repo, "add", ".")
            _git(repo, "commit", "-q", "-m", "original")
            shutil.copy(work / "python_eval" / "clean_amounts_fix_safe.py", repo / "etl" / "clean_amounts.py")
            print("=" * 78 + "\nOne-line usage in a git repo:  fixwitness check etl/clean_amounts.py\n" + "=" * 78)
            old = os.getcwd()
            os.chdir(repo)
            try:
                print(markdown(run_check(load_config(None, {"path": "etl/clean_amounts.py"}))))
            finally:
                os.chdir(old)
        return 0


def cmd_categories(args: argparse.Namespace) -> int:
    from fixwitness.formats import JSON_CATEGORY_DESCRIPTIONS
    for name, desc in CATEGORY_DESCRIPTIONS.items():
        print(f"{name:15} {DEFAULT_KIND[name]:7} {desc}")
    for name, desc in JSON_CATEGORY_DESCRIPTIONS.items():
        print(f"{name:15} {'valid':7} {desc} (JSON inputs)")
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from fixwitness.mcp_server import serve
    return serve()


def _selection_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("path", nargs="?", help="the file you changed (compared with git --base, default HEAD)")
    p.add_argument("--sample", help="sample input CSV with a header row (found automatically if there is one)")
    p.add_argument("--base", help="git revision holding the original (default HEAD)")
    p.add_argument("--command", help="entry command for fixes spread over several files, run in the repo root, "
                                     "e.g. 'python3 etl/run.py {input} {output}'")
    p.add_argument("--before", help="original file (no git needed)")
    p.add_argument("--after", help="fixed file (no git needed)")
    p.add_argument("--run", help="how to run one script, e.g. 'python3 {script} {input} {output}' (auto-detected)")
    p.add_argument("--incident", help="for self-healing repairs: the input that broke the original; "
                                      "the fix must process it")
    p.add_argument("--incident-expected", help="optional: the correct output for the incident input")
    p.add_argument("--no-attacks", action="store_true", help="skip attack payloads (repairs and refactors)")
    p.add_argument("--table", action="append", metavar="NAME=FILE",
                   help="SQL/dbt: a table the query reads and its sample CSV (repeatable)")
    p.add_argument("--incident-table", action="append", metavar="NAME=FILE",
                   help="SQL/dbt: a table's contents when the original broke (repeatable)")
    p.add_argument("--engine", choices=["auto", "duckdb", "sqlite"],
                   help="SQL/dbt: query engine (default: DuckDB if installed, else SQLite)")
    p.add_argument("--sql-ordered", "--ordered", dest="sql_ordered", action="store_true",
                   help="SQL/dbt and DataFrames: compare result rows in order (default: as a set of rows)")
    p.add_argument("--warehouse", metavar="URL",
                   help="SQL/dbt: run both versions in your warehouse (postgres://USER@HOST/DB, "
                        "snowflake://USER@ACCOUNT/DB?warehouse=WH, bigquery://PROJECT); password from the driver's "
                        "own setting, never the URL")
    p.add_argument("--manifest", metavar="FILE", help="dbt: the fix's target/manifest.json (from dbt compile)")
    p.add_argument("--base-manifest", metavar="FILE", help="dbt: the original's manifest.json")
    p.add_argument("--function", metavar="NAME",
                   help="Python DataFrame code: the function to call with the tables (pandas, polars or PySpark)")
    p.add_argument("--library", choices=["auto", "pandas", "polars", "pyspark"],
                   help="DataFrame library (default: from the script's imports)")
    p.add_argument("--dialect", help="SQL/dbt: the warehouse the SQL is written for (snowflake, bigquery, "
                                     "postgres, tsql, ...); translated with sqlglot to the engine")
    p.add_argument("--sql-outputs", metavar="MODEL,...",
                   help="SQL/dbt folder of models: the models to compare (default: the final ones; 'all' for every model)")
    p.add_argument("--run-after", help="run command for the fix when it differs (e.g. a rewrite in another language)")
    p.add_argument("--columns", help="comma-separated columns to probe (default: all)")
    p.add_argument("--review", help="comma-separated categories where differences are expected")
    p.add_argument("--output", choices=["csv", "json", "text"],
                   help="how to compare outputs (default: json for JSON inputs, else csv)")
    p.add_argument("--ignore-columns", help="comma-separated output columns to leave out of the comparison")
    p.add_argument("--expect-change", metavar="COLUMNS",
                   help="for a bug fix: the output columns it should change (model.column or column, comma-separated); "
                        "the check passes when nothing else changes")
    p.add_argument("--ignore-pattern", action="append", help="regex masked out of every compared value (repeatable)")
    p.add_argument("--tolerance", type=float, help="relative tolerance for numeric values, e.g. 1e-9")
    p.add_argument("--unordered", action="store_true", help="ignore row order")
    p.add_argument("--no-auto-ignore", action="store_true", help="don't ignore columns that are not deterministic")
    p.add_argument("--no-shrink", action="store_true",
                   help="don't shrink each difference to the smallest input that shows it")
    p.add_argument("--no-exercise-check", action="store_true",
                   help="don't turn a PASS into INCONCLUSIVE when no input reaches what the change touched")
    p.add_argument("--strict-robustness", action="store_true",
                   help="fail a data change that crashes on a malformed-text input the original ran "
                        "(by default that is reported as a robustness finding)")
    p.add_argument("--same-numbers", action="store_true",
                   help="compare numbers by value: \"1\" and \"1.0\", \"1e+30\" and \"1e30\" are the same "
                        "(for library migrations; by default an integer turning into a decimal is a change)")
    p.add_argument("--max-cases", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--timeout", type=float, help="seconds per run (default 10)")
    p.add_argument("--workers", type=int, help="parallel cases (default: up to 8)")
    p.add_argument("--pass-env", action="append", help="environment variable to pass through (repeatable)")
    p.add_argument("--allow-any-command", action="store_true", help="allow programs outside the allow-list")
    p.add_argument("--no-network", action="store_true", help="run scripts without network access (Linux)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fixwitness",
                                     description="Evidence that an automated fix (security patch or self-healing repair) fixed the problem without changing your data.")
    parser.add_argument("--version", action="version", version=f"fixwitness {__version__}")
    sub = parser.add_subparsers(dest="command_name", required=True)

    check = sub.add_parser("check", help="compare the original with the fix")
    _selection_args(check)
    check.add_argument("--config", help="TOML config (default: ./fixwitness.toml when no file is given)")
    check.add_argument("--out-dir", default=".fixwitness", help="where to write proof.json, report.md and report.html")
    check.add_argument("--open", action="store_true", help="open report.html in your browser when the check ends")
    check.add_argument("--min-confidence", type=int, default=0, help="fail if confidence is below this")
    check.add_argument("--json", action="store_true", help="print JSON instead of the summary")
    check.add_argument("--dry-run", action="store_true", help="show what would be compared, without comparing")
    check.set_defaults(func=cmd_check)

    init = sub.add_parser("init", help="detect settings and save them to fixwitness.toml")
    _selection_args(init)
    init.add_argument("--write", default="fixwitness.toml", help="file to write")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")
    init.set_defaults(func=cmd_init)

    rp = sub.add_parser("replay", help="re-run a saved proof and check it reproduces")
    rp.add_argument("proof", help="path to proof.json")
    rp.add_argument("--allow-any-command", action="store_true")
    rp.set_defaults(func=cmd_replay)

    acc = sub.add_parser("accept", help="mark a difference as intended (recorded in fixwitness.toml)")
    acc.add_argument("--category", required=True, help="the input category, e.g. case or null-column")
    acc.add_argument("--column", help="the column it is about, e.g. orders.status (default: any column)")
    acc.add_argument("--target", help="the changed file it is about, e.g. models/revenue.sql (default: any)")
    acc.add_argument("--note", help="why the difference is intended")
    acc.add_argument("--config", help="settings file to write (default: ./fixwitness.toml)")
    acc.set_defaults(func=cmd_accept)
    st = sub.add_parser("setup", help="connect fixwitness to Claude Code, Cursor, VS Code, GitHub or pre-commit")
    st.add_argument("target", choices=["claude", "cursor", "vscode", "github", "pre-commit"])
    st.add_argument("--instructions", action="store_true",
                    help="also tell coding agents (CLAUDE.md or AGENTS.md) to call prove_change before finishing")
    st.set_defaults(func=cmd_setup)
    dr = sub.add_parser("doctor", help="say whether this repository is ready to check, and what to install")
    dr.add_argument("--base", help="git revision to compare with (default HEAD)")
    dr.add_argument("--warehouse", help="also check this warehouse (postgres://USER@HOST/DB, ...)")
    dr.add_argument("--no-connect", action="store_true", help="don't connect to the warehouse")
    dr.set_defaults(func=cmd_doctor)
    ui = sub.add_parser("ui", help="open the local web app: run checks, read reports, mark differences as intended")
    ui.add_argument("--port", type=int, default=0, help="port on 127.0.0.1 (default: any free port)")
    ui.add_argument("--no-browser", action="store_true", help="don't open a browser window")
    ui.set_defaults(func=cmd_ui)
    sub.add_parser("demo", help="run the built-in examples").set_defaults(func=cmd_demo)
    sub.add_parser("categories", help="list the input categories fixwitness generates").set_defaults(func=cmd_categories)
    sub.add_parser("mcp", help="start the MCP server on stdio").set_defaults(func=cmd_mcp)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, RunConfigError, SampleError) as exc:
        print(f"fixwitness: {exc}", file=sys.stderr)
        return 2
