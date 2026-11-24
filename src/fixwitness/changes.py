"""Check everything a change touched, with no setup: `fixwitness check` with no file named.

Each changed file is classified and checked the way that fits it:

  in a dbt project (models, macros, seeds)  the project, compiled by dbt, finals downstream compared
  a .sql file                               a query; its tables found by name among the data files
  a .py file with changed DataFrame          each changed function, called with tables found by name
    functions (pandas, polars, PySpark)       (from its parameter names)
  a runnable script (Python, shell, ...)    run on its sample (CSV, JSON, JSON Lines or Parquet)

Files that are not code (docs, data, config) are listed as not checked. The combined verdict is
FAIL if any check fails, PASS if every check passes, and INCONCLUSIVE otherwise.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from pathlib import Path

from fixwitness.config import Config, ConfigError
from fixwitness.plan import PlanError, _git, changed_files, program_for, repo_root

CODE_SUFFIXES = {".py", ".sh", ".bash", ".js", ".mjs", ".ts", ".rb", ".pl", ".php", ".r", ".R", ".sql"}
TEST_FILE = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|conftest\.py$)")


@dataclass
class Item:
    target: str                  # what the report calls it, e.g. "etl/revenue.py: revenue()"
    kind: str                    # dbt, sql, dataframe, script
    overrides: dict = field(default_factory=dict)


def _show(root: Path, commit: str, rel: str) -> str | None:
    try:
        return _git(["show", f"{commit}:{rel}"], root)
    except Exception:
        return None


def plan_items(cfg: Config) -> tuple[list[Item], list[tuple[str, str]]]:
    """The checks to run for the working tree's changes against cfg.base (or for cfg.path only)."""
    from fixwitness.dbtmode import find_project
    from fixwitness.discover import frame_functions, is_runnable_script
    anchor = cfg.resolve(cfg.path) if cfg.path else cfg.base_dir
    root = repo_root(anchor if anchor.is_dir() else anchor.parent)
    commit = _git(["rev-parse", "--verify", f"{cfg.base}^{{commit}}"], root).strip()
    changes = changed_files(root, commit)
    if cfg.path:
        rel = anchor.resolve().relative_to(root.resolve()).as_posix()
        changes = [(st, p) for st, p in changes if rel in (".", p) or p.startswith(rel.rstrip("/") + "/")] \
            or [("M", rel)]
    items: list[Item] = []
    skipped: list[tuple[str, str]] = []
    projects: dict[str, Path] = {}
    from fixwitness.adapters import claim, load_adapters
    adapters = load_adapters(root)
    for status, rel in changes:
        path = root / rel
        if adapters and path.is_file() and not status.startswith(("D", "A")) and status != "??":
            got = claim(adapters, path, root)
            if got is not None:
                kind, settings = got
                settings.pop("allow_any_command", None)  # only the user can lift the program allow-list
                for key in ("sample", "incident", "incident_expected", "before", "after"):
                    if isinstance(settings.get(key), str) and not Path(settings[key]).is_absolute():
                        settings[key] = str(root / settings[key])
                items.append(Item(rel, kind, {"path": str(path), **settings}))
                continue
        project = find_project(path if path.exists() else path.parent, root) if cfg.dbt != "off" else None
        if project is not None and Path(rel).suffix.lower() in (".sql", ".yml", ".yaml", ".csv", ".md") \
                and "target/" not in rel and "dbt_packages/" not in rel and not Path(rel).name.startswith("."):
            if Path(rel).suffix.lower() in (".md",):
                skipped.append((rel, "documentation"))
                continue
            from fixwitness.dbtmode import runnable_project
            project = runnable_project(project)  # a package: compiled through its integration tests
            projects.setdefault(project.relative_to(root).as_posix() or ".", project)
            continue
        if status.startswith("D"):
            skipped.append((rel, "deleted: nothing to run"))
            continue
        if status.startswith("A") or status == "??":
            skipped.append((rel, "new file: there is no original to compare"))
            continue
        suffix = path.suffix
        if suffix not in CODE_SUFFIXES and not (path.is_file() and program_for(path)):
            skipped.append((rel, "not code"))
            continue
        if TEST_FILE.search(rel):
            skipped.append((rel, "a test file"))
            continue
        if suffix.lower() == ".sql":
            items.append(Item(rel, "sql", {"path": str(path)}))
            continue
        if suffix == ".py":
            before, after = _show(root, commit, rel) or "", path.read_text(encoding="utf-8", errors="replace")
            roots = [path.parent, *path.parent.parents[:3], root]
            if cfg.function:
                items.append(Item(f"{rel}: {cfg.function}()", "dataframe", {"path": str(path)}))
                continue
            funcs = frame_functions(before, after, list(dict.fromkeys(roots)))
            for name, tables in funcs:
                items.append(Item(f"{rel}: {name}()", "dataframe",
                                  {"path": str(path), "function": name,
                                   "tables": {t: str(p) for t, p in tables.items()}}))
            if funcs:
                continue
            if not is_runnable_script(after):
                skipped.append((rel, "a module with no changed function that takes tables (name the parameters "
                                     "after data files, or pass --function and --table)"))
                continue
        items.append(Item(rel, "script", {"path": str(path)}))
    from fixwitness.dbtmode import dbt_available, project_settings
    for prel, project in sorted(projects.items()):
        target = project
        if not (dbt_available() or cfg.manifest):  # rendered by fixwitness: only the models folder
            paths = project_settings(project).get("model-paths") or ["models"]
            target = project / paths[0]
        items.insert(0, Item(f"{prel} (dbt project)", "dbt", {"path": str(target)}))
    return items, skipped


def run_items(cfg: Config, items: list[Item], out_dir: Path | None = None) -> dict:
    from fixwitness.core import run_check
    from fixwitness.report import write_outputs
    results = []
    for i, item in enumerate(items):
        try:
            sub = dataclasses.replace(cfg, **{k: v for k, v in item.overrides.items()})
        except TypeError as exc:  # an adapter gave a setting fixwitness doesn't have
            results.append({"target": item.target, "kind": item.kind, "verdict": "NOT CHECKED",
                            "reason": f"unknown setting from the adapter: {exc}", "proof": None})
            continue
        if item.kind != "dataframe":
            sub = dataclasses.replace(sub, function=None) if not cfg.function else sub
        try:
            sub.validate()
            proof = run_check(sub)
        except (PlanError, ConfigError) as exc:
            results.append({"target": item.target, "kind": item.kind, "verdict": "NOT CHECKED",
                            "reason": str(exc).splitlines()[0][:300], "proof": None,
                            "detail": "\n".join(str(exc).splitlines()[1:])[-4000:] or None})
            continue
        first = next((d.get("explanation") for d in proof["differences"]
                      if d["kind"] != "review" and d.get("explanation")), None)
        entry = {"target": item.target, "kind": item.kind, "verdict": proof["verdict"],
                 "score": proof["confidence"]["score"], "reason": first or "; ".join(proof["reasons"]) or "-",
                 "proof_id": proof["proof_id"][:16], "proof": None, "_proof": proof}
        if out_dir is not None:
            slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.target).strip("_")[:80] or f"check{i}"
            entry["proof"] = str(write_outputs(proof, out_dir / slug))
        results.append(entry)
    verdicts = [r["verdict"] for r in results]
    if "FAIL" in verdicts:
        verdict = "FAIL"
    elif verdicts and all(v == "PASS" for v in verdicts):
        verdict = "PASS"
    else:
        verdict = "INCONCLUSIVE"
    return {"verdict": verdict, "checks": results}


def summary_markdown(result: dict, skipped: list[tuple[str, str]]) -> str:
    from fixwitness.report import markdown
    icon = {"PASS": "PASS", "FAIL": "**FAIL**", "INCONCLUSIVE": "INCONCLUSIVE", "NOT CHECKED": "not checked"}
    lines = [f"## fixwitness: {result['verdict']} ({len(result['checks'])} check"
             f"{'s' if len(result['checks']) != 1 else ''})", "",
             "| Changed | Checked as | Result | Why |", "|---|---|---|---|"]
    for r in result["checks"]:
        res = icon.get(r["verdict"], r["verdict"]) + (f" {r['score']}/100" if r["verdict"] == "PASS" else "")
        lines.append(f"| `{r['target']}` | {r['kind']} | {res} | {r['reason']} |")
    if skipped:
        lines += ["", "Not checked: " + "; ".join(f"`{p}` ({why})" for p, why in skipped)]
    if any(r["verdict"] == "NOT CHECKED" for r in result["checks"]):
        lines += ["", "To see what is missing and the command that fixes it: `fixwitness doctor`."]
    for r in result["checks"]:
        if r.get("_proof") is not None and r["verdict"] != "PASS":
            lines += ["", "---", "", f"### `{r['target']}`", ""]
            lines += markdown(r["_proof"], r.get("proof")).splitlines()[1:]
    return "\n".join(lines) + "\n"
