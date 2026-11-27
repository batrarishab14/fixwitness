"""fixwitness doctor: is this repository ready to check, and what is missing?

    fixwitness doctor                     what `fixwitness check` would check here, and with what
    fixwitness doctor --warehouse URL     also: is the warehouse reachable (creates and drops a schema)

Nothing is changed. Each line says what was found; each problem says the one command that fixes it.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

OK, MISSING, INFO = "ok", "missing", "info"


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _version(dist: str) -> str | None:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version(dist)
    except PackageNotFoundError:
        return None


def checks(root: Path, base: str | None = None, warehouse: str | None = None, connect: bool = False) -> list[dict]:
    """[{status, what, fix}] in the order they are shown."""
    from fixwitness import __version__
    out: list[dict] = []

    def add(status: str, what: str, fix: str | None = None) -> None:
        out.append({"status": status, "what": what, "fix": fix})

    add(OK, f"fixwitness {__version__} on Python {sys.version.split()[0]}")
    git_ok = shutil.which("git") is not None
    inside = git_ok and subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root,
                                       capture_output=True, text=True).returncode == 0
    if not inside:
        add(MISSING, "a git repository: `fixwitness check` with no file compares your changes with a commit",
            "run it inside your repository, or compare two files: fixwitness check --before old.sql --after new.sql")
    else:
        ref = base or "HEAD"
        has_ref = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=root,
                                 capture_output=True, text=True).returncode == 0
        add(OK if has_ref else MISSING, f"git base {ref}" + ("" if has_ref else " not found"),
            None if has_ref else ("make a first commit" if ref == "HEAD" else f"git fetch origin {ref}"))

    # What would be checked, and with which kind.
    kinds: set[str] = set()
    if inside:
        try:
            from fixwitness.changes import plan_items
            from fixwitness.config import load_config
            items, skipped = plan_items(load_config(None, {"base": base}))
            if not items:
                add(INFO, "no changed data code yet: edit a model, query, DataFrame function or script, then check")
            for it in items:
                kinds.add(it.kind)
                add(OK, f"will check {it.target} as {it.kind}")
            for path, why in skipped[:8]:
                add(INFO, f"not checked: {path} ({why})")
            if len(skipped) > 8:
                add(INFO, f"and {len(skipped) - 8} more files not checked")
        except Exception as exc:  # report, never crash: the doctor runs when things are broken
            add(MISSING, f"could not list the change: {str(exc).splitlines()[0][:200]}")

    # dbt projects: dbt itself, the adapter, the project to build, and its seeds.
    from fixwitness.dbtmode import ADAPTER_PIP, _has_seeds, runnable_project
    projects = sorted({p.parent for p in root.rglob("dbt_project.yml")
                       if not any(part in ("dbt_packages", "target", ".git", "node_modules") for part in p.parts)})
    projects = [p for p in projects if not (p.parent / "dbt_project.yml").is_file()]  # top-level ones
    adapter = "duckdb"
    if warehouse:
        from fixwitness.warehouse import WarehouseError, parse_url
        try:
            adapter = parse_url(warehouse)["kind"]
        except WarehouseError as exc:
            add(MISSING, f"warehouse URL: {exc}")
    for p in projects[:5]:
        rel = p.relative_to(root).as_posix() or "."
        run = runnable_project(p)
        how = f" (built through {run.relative_to(root).as_posix()}/, its integration tests)" if run != p else ""
        add(OK if _has_seeds(run) else INFO, f"dbt project {rel}{how}: "
            + ("seeds found, used as the sample tables" if _has_seeds(run) else
               "no seeds: give each source a sample with --table NAME=FILE.csv"))
    if projects or "dbt" in kinds:
        core = _version("dbt-core")
        add(OK if core else MISSING, f"dbt-core {core}" if core else "dbt-core (to build the project with dbt itself)",
            None if core else f"pip install dbt-core {ADAPTER_PIP[adapter]}")
        have = _has(f"dbt.adapters.{adapter}")
        add(OK if have else MISSING, f"{ADAPTER_PIP[adapter]} {_version(ADAPTER_PIP[adapter]) or ''}".strip()
            if have else f"{ADAPTER_PIP[adapter]} (dbt's adapter for {adapter})",
            None if have else f"pip install {ADAPTER_PIP[adapter]}")

    # Engines and libraries.
    if _has("duckdb"):
        add(OK, f"duckdb {_version('duckdb')}: SQL runs on DuckDB")
    else:
        add(INFO, "duckdb not installed: SQL runs on SQLite, whose SQL differs from warehouses'",
            "pip install duckdb")
    if not _has("sqlglot"):
        add(INFO, "sqlglot not installed: needed only for SQL written for a warehouse (--dialect)", "pip install sqlglot")
    for lib in ("pandas", "polars", "pyarrow"):
        if "dataframe" in kinds and not _has(lib):
            add(INFO, f"{lib} not installed (only needed if your code uses it)", f"pip install {lib}")

    # The warehouse, if one is named.
    if warehouse:
        from fixwitness.warehouse import DRIVER, SECRET_ENV, WarehouseError, check_url
        try:
            kind = check_url(warehouse)
            add(OK, f"warehouse {warehouse}: driver {DRIVER[kind]} installed")
            secrets = [v for v in SECRET_ENV[kind] if os.environ.get(v)]
            add(OK if secrets or kind == "bigquery" else INFO,
                f"credentials from {', '.join(secrets)}" if secrets else
                f"no {SECRET_ENV[kind][0]} set: the driver's other settings are used (e.g. ~/.pgpass)")
            if connect:
                from fixwitness.warehouse import Session
                with Session(warehouse) as s:
                    add(OK, f"connected: created and dropped the private schema {s.schema}")
        except WarehouseError as exc:
            text = str(exc)
            add(MISSING, f"warehouse: {text}", "pip install " + text.split("pip install ", 1)[1]
                if "pip install " in text else None)
        except Exception as exc:
            add(MISSING, f"could not connect to {warehouse}: {str(exc).splitlines()[0][:200]}",
                "check the host, user and database in the URL, and the password variable")

    from fixwitness.dbtmode import cache_dir
    cache = cache_dir()
    add(INFO, f"dbt compiles are reused from {cache}" if cache else "dbt compile cache is off")
    return out


def render(items: list[dict]) -> tuple[str, bool]:
    marks = {OK: "✓", MISSING: "✗", INFO: "·"}
    lines = ["fixwitness doctor", ""]
    for it in items:
        lines.append(f"  {marks[it['status']]} {it['what']}")
        if it["fix"] and it["status"] != OK:
            lines.append(f"      → {it['fix']}")
    ready = not any(it["status"] == MISSING for it in items)
    fixes = [it["fix"] for it in items if it["status"] == MISSING and it["fix"]]
    lines += ["", "Ready: run `fixwitness check`." if ready else
              "Not ready yet. Fix the ✗ lines" + (f", starting with: {fixes[0]}" if fixes else "") + "."]
    return "\n".join(lines) + "\n", ready
