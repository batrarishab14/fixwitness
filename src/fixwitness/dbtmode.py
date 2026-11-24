"""dbt projects with no setup: dbt itself renders the models, fixwitness runs them on generated data.

1. Compile. For each version of the project, fixwitness runs `dbt seed` and `dbt compile` with
   the dbt-duckdb adapter in a private DuckDB file, so macros, packages, `var()` and
   `is_incremental()` are rendered by dbt itself, for DuckDB. Or it reads the manifest.json files
   your CI already produced (`--manifest`, `--base-manifest`), compiled for your warehouse, and
   translates them with sqlglot.
2. Read the manifest: every SQL model's compiled code, the dependency graph, the seeds and the
   sources. Relation names such as "memory"."main"."stg_orders" become the bare table name.
3. Find what changed: the models whose compiled SQL differs. The models compared are the final
   models downstream of a change (no other model reads them), so a staging change is judged by
   what it does to the marts.
4. Tables: the seeds, and a sample for each source (found by name in the project's data folders,
   or given with --table).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

SEED_ROWS = 200      # seeds are samples: the first rows are enough, and keep every case small
ORDER_FILE = "fixwitness_order.txt"


class DbtError(Exception):
    pass


@dataclass
class Graph:
    adapter: str
    models: dict[str, str] = field(default_factory=dict)          # name -> compiled SQL
    depends: dict[str, set[str]] = field(default_factory=dict)    # model -> models it reads
    relations: dict[str, str] = field(default_factory=dict)       # relation name -> bare table name
    seeds: dict[str, Path] = field(default_factory=dict)          # seed name -> CSV file
    sources: dict[str, tuple[str, str]] = field(default_factory=dict)  # table name -> (source, table)
    skipped: list[str] = field(default_factory=list)


def find_project(path: Path, stop: Path) -> Path | None:
    """The folder holding dbt_project.yml at or above path (not above stop)."""
    cur = path if path.is_dir() else path.parent
    stop = stop.resolve()
    while True:
        if (cur / "dbt_project.yml").is_file():
            return cur
        if cur.resolve() == stop or cur.parent == cur:
            return None
        cur = cur.parent


def project_settings(project: Path) -> dict:
    text = (project / "dbt_project.yml").read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text) or {}
    except Exception:  # no PyYAML: the two keys needed are simple
        data = {}
        for key in ("name", "profile"):
            m = re.search(rf"^{key}\s*:\s*['\"]?([\w-]+)", text, re.M)
            if m:
                data[key] = m.group(1)
    return data


def dbt_available() -> bool:
    return shutil.which("dbt") is not None and importlib.util.find_spec("dbt.adapters.duckdb") is not None


def _run(args: list[str], project: Path, env: dict, timeout: int) -> None:
    try:
        proc = subprocess.run(args, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise DbtError(f"`{' '.join(args[:2])}` took longer than {timeout}s") from None
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-12:])
        raise DbtError(f"`{' '.join(args[:2])}` failed in {project.name}:\n{tail}")


def compile_project(project: Path, out: Path, timeout: int = 900) -> Path:
    """Run dbt seed + dbt compile with a private DuckDB profile; return the manifest path."""
    if not dbt_available():
        raise DbtError("compiling a dbt project needs dbt-core and the dbt-duckdb adapter: "
                       "pip install dbt-core dbt-duckdb (or pass --manifest and --base-manifest)")
    settings = project_settings(project)
    profile = settings.get("profile") or settings.get("name") or "default"
    out.mkdir(parents=True, exist_ok=True)
    profiles = out / "profiles"
    profiles.mkdir(exist_ok=True)
    db = out / "fixwitness.duckdb"
    (profiles / "profiles.yml").write_text(
        f"{profile}:\n  target: fixwitness\n  outputs:\n    fixwitness:\n      type: duckdb\n"
        f"      path: {json.dumps(str(db))}\n      threads: 1\n", encoding="utf-8")
    env = dict(os.environ, DBT_PROFILES_DIR=str(profiles), DBT_SEND_ANONYMOUS_USAGE_STATS="false",
               DBT_TARGET_PATH=str(out / "target"), DBT_LOG_PATH=str(out / "logs"))
    common = ["--project-dir", str(project), "--profiles-dir", str(profiles), "--target", "fixwitness"]
    if ((project / "packages.yml").exists() or (project / "dependencies.yml").exists()) \
            and not (project / "dbt_packages").exists():
        _run(["dbt", "deps", *common], project, env, timeout)
    settings_seeds = settings.get("seed-paths") or ["seeds"]
    if any((project / p).is_dir() and any((project / p).rglob("*.csv")) for p in settings_seeds):
        # Seeds loaded first, so macros that look at a table's columns (dbt_utils.star) can compile.
        _run(["dbt", "seed", *common], project, env, timeout)
    _run(["dbt", "compile", *common], project, env, timeout)
    manifest = out / "target" / "manifest.json"
    if not manifest.is_file():
        raise DbtError(f"dbt compile wrote no manifest for {project.name}")
    return manifest


def read_manifest(manifest_path: Path, project: Path | None) -> Graph:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    g = Graph(adapter=meta.get("adapter_type") or "duckdb")
    nodes = data.get("nodes", {})
    project_name = (data.get("metadata") or {}).get("project_name")
    by_id = {}
    ephemeral: dict[str, list[str]] = {}
    for uid, n in nodes.items():
        kind = n.get("resource_type")
        if kind == "seed":
            root = project or Path(n.get("root_path") or ".")
            if project is not None and n.get("package_name") not in (None, project_name):
                root = project / "dbt_packages" / n["package_name"]
            g.seeds[n["name"]] = root / n["original_file_path"]
            by_id[uid] = n["name"]
            if n.get("relation_name"):
                g.relations[n["relation_name"]] = n["name"]
        elif kind == "model":
            mat = (n.get("config") or {}).get("materialized")
            if n.get("language", "sql") != "sql":
                g.skipped.append(f"{n['name']} ({n.get('language')} model)")
                continue
            if mat == "ephemeral":  # inlined by dbt into the models that use it
                ephemeral[uid] = list((n.get("depends_on") or {}).get("nodes", []))
                continue
            code = n.get("compiled_code") or n.get("compiled_sql")
            if code is None:
                raise DbtError(f"the manifest has no compiled SQL for {n['name']}: run `dbt compile`, not `dbt parse`")
            g.models[n["name"]] = code
            by_id[uid] = n["name"]
            if n.get("relation_name"):
                g.relations[n["relation_name"]] = n["name"]
    for uid, src in (data.get("sources") or {}).items():
        table = src.get("identifier") or src["name"]
        if table in g.models or table in g.seeds or table in g.sources:
            table = f"{src['source_name']}__{src['name']}"  # a source named like a model or another source
        g.sources[table] = (src["source_name"], src["name"])
        by_id[uid] = table
        if src.get("relation_name"):
            g.relations[src["relation_name"]] = table

    def resolve(ids: list[str], seen: set[str]) -> set[str]:
        out = set()
        for d in ids:
            if d in ephemeral and d not in seen:
                out |= resolve(ephemeral[d], seen | {d})
            elif d in by_id and by_id[d] in g.models:
                out.add(by_id[d])
        return out

    for uid, n in nodes.items():
        if n.get("resource_type") == "model" and n.get("name") in g.models:
            g.depends[n["name"]] = resolve(list((n.get("depends_on") or {}).get("nodes", [])), set())
    return g


def bare_sql(g: Graph, name: str) -> str:
    """A model's compiled SQL with every relation name replaced by its bare, quoted table name."""
    sql = g.models[name]
    for rel in sorted(g.relations, key=len, reverse=True):
        sql = sql.replace(rel, '"' + g.relations[rel].replace('"', '""') + '"')
    return sql


def order(g: Graph) -> list[str]:
    done, out = set(), []
    while len(out) < len(g.models):
        ready = sorted(m for m in g.models if m not in done and g.depends.get(m, set()) <= done)
        if not ready:
            raise DbtError("the models depend on each other in a cycle: " + ", ".join(sorted(set(g.models) - done)))
        out += ready
        done |= set(ready)
    return out


def write_models(g: Graph, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in g.models:
        (dest / f"{name}.sql").write_text(bare_sql(g, name).strip() + "\n", encoding="utf-8")
    (dest / ORDER_FILE).write_text("\n".join(order(g)) + "\n", encoding="utf-8")


def _norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def changed_models(g0: Graph, g1: Graph) -> list[str]:
    names = set(g0.models) | set(g1.models)
    return sorted(n for n in names if n not in g0.models or n not in g1.models
                  or _norm(bare_sql(g0, n)) != _norm(bare_sql(g1, n)))


def final_downstream(g: Graph, changed: list[str]) -> list[str]:
    """The original's final models (no model reads them) that depend on a changed model, or are one."""
    readers: dict[str, set[str]] = {m: set() for m in g.models}
    for m, deps in g.depends.items():
        for d in deps:
            readers.setdefault(d, set()).add(m)
    reach, todo = set(), [c for c in changed if c in g.models]
    while todo:
        m = todo.pop()
        if m in reach:
            continue
        reach.add(m)
        todo += list(readers.get(m, ()))
    finals = sorted(m for m in reach if not readers.get(m))
    if not finals:  # a removed model: compare what read it in the original
        finals = sorted({r for c in changed for r in readers.get(c, ())})
    return finals


def seed_sample(path: Path, dest: Path) -> Path:
    """The seed itself, or its header and first SEED_ROWS rows when it is longer."""
    import csv
    import itertools
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(itertools.islice(csv.reader(fh), SEED_ROWS + 2))
    if len(rows) <= SEED_ROWS + 1:
        return path
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows[: SEED_ROWS + 1])
    return dest
