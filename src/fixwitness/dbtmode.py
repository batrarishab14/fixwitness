"""dbt projects with no setup: dbt itself renders the models, fixwitness runs them on generated data.

1. Compile. For each version of the project, fixwitness runs `dbt seed`, `dbt run` and
   `dbt compile` with the dbt-duckdb adapter in a private DuckDB file, so macros, packages,
   `var()` and `is_incremental()` are rendered by dbt itself, for DuckDB, and macros that read a
   model's columns (dbt_utils.star, adapter.get_columns_in_relation) see the real columns. Or it
   reads the manifest.json files your CI already produced (`--manifest`, `--base-manifest`),
   compiled for your warehouse, and translates them with sqlglot.
   A dbt package is compiled through its integration-test project (integration_tests/, which
   installs the package from ../ and holds the seeds), and when the sources point at the seeds
   through a schema variable, the private target schema is set to that schema.
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
DEPS_FILE = "fixwitness_deps.json"    # each model's models, from dbt's graph: only what an output needs runs


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
    try:
        found = importlib.util.find_spec("dbt.adapters.duckdb") is not None
    except ModuleNotFoundError:
        found = False
    return shutil.which("dbt") is not None and found


def _has_seeds(project: Path) -> bool:
    paths = project_settings(project).get("seed-paths") or ["seeds"]
    return any((project / p).is_dir() and any((project / p).rglob("*.csv")) for p in paths)


def runnable_project(project: Path) -> Path:
    """The project to compile for a change to `project`: itself, or, for a dbt package with no seeds
    of its own, the integration-test project inside it that installs it from a local path."""
    if _has_seeds(project):
        return project
    for child in sorted(project.iterdir()) if project.is_dir() else []:
        if not child.is_dir() or child.name.startswith((".", "dbt_packages", "target")):
            continue
        if not (child / "dbt_project.yml").is_file() or not _has_seeds(child):
            continue
        for name in ("packages.yml", "dependencies.yml"):
            f = child / name
            if f.is_file() and re.search(r"^\s*-?\s*local\s*:\s*['\"]?\.\.[/\\]?['\"]?\s*$",
                                         f.read_text(encoding="utf-8"), re.M):
                return child
    return project


def _run(args: list[str], project: Path, env: dict, timeout: int) -> None:
    try:
        proc = subprocess.run(args, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise DbtError(f"`{' '.join(args[:2])}` took longer than {timeout}s") from None
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-12:])
        raise DbtError(f"`{' '.join(args[:2])}` failed in {project.name}:\n{tail}")


def _profile(path: Path, name: str, db: Path, schema: str) -> None:
    path.write_text(
        f"{name}:\n  target: fixwitness\n  outputs:\n    fixwitness:\n      type: duckdb\n"
        f"      path: {json.dumps(str(db))}\n      schema: {json.dumps(schema)}\n      threads: 1\n",
        encoding="utf-8")


def source_schema(manifest: Path) -> str | None:
    """The one schema that the sources reading seeds point at (a package's integration tests set it
    with a variable), when it is not the default; None otherwise."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    seeds = set()
    for n in (data.get("nodes") or {}).values():
        if n.get("resource_type") == "seed":
            seeds |= {n.get("alias") or n["name"], n["name"]}
    schemas = {src.get("schema") for src in (data.get("sources") or {}).values()
               if (src.get("identifier") or src.get("name")) in seeds and src.get("schema")}
    return schemas.pop() if len(schemas) == 1 and schemas != {"main"} else None


def compile_project(project: Path, out: Path, timeout: int = 900, notes: list[str] | None = None) -> Path:
    """dbt seed, dbt run and dbt compile in a private DuckDB file; return the manifest path."""
    if not dbt_available():
        raise DbtError("compiling a dbt project needs dbt-core and the dbt-duckdb adapter: "
                       "pip install dbt-core dbt-duckdb (or pass --manifest and --base-manifest)")
    settings = project_settings(project)
    profile = settings.get("profile") or settings.get("name") or "default"
    out.mkdir(parents=True, exist_ok=True)
    profiles = out / "profiles"
    profiles.mkdir(exist_ok=True)
    db = out / "fixwitness.duckdb"
    _profile(profiles / "profiles.yml", profile, db, "main")
    env = dict(os.environ, DBT_PROFILES_DIR=str(profiles), DBT_SEND_ANONYMOUS_USAGE_STATS="false",
               DBT_TARGET_PATH=str(out / "target"), DBT_LOG_PATH=str(out / "logs"))
    common = ["--project-dir", str(project), "--profiles-dir", str(profiles), "--target", "fixwitness"]
    if ((project / "packages.yml").exists() or (project / "dependencies.yml").exists()) \
            and not (project / "dbt_packages").exists():
        _run(["dbt", "deps", *common], project, env, timeout)
    seeds = _has_seeds(project)
    if seeds:
        # Sources that read the seeds through a schema variable: the target schema is set to it, so
        # the seeds load where the sources look for them.
        _run(["dbt", "parse", *common], project, env, timeout)
        schema = source_schema(out / "target" / "manifest.json")
        if schema:
            _profile(profiles / "profiles.yml", profile, db, schema)
        _run(["dbt", "seed", *common], project, env, timeout)
        # Built once on the seeds, so macros that read a model's columns or query a model while
        # compiling see the real tables. A model that fails to build here is still compiled.
        try:
            _run(["dbt", "run", *common], project, env, timeout)
        except DbtError as exc:
            if notes is not None:
                first = next((l for l in str(exc).splitlines()[1:] if "rror" in l), "")
                notes.append(f"dbt: `dbt run` on the seeds failed in {project.name} ({first.strip()[:160]}); "
                             f"models were still compiled, but macros that read a model's columns may "
                             f"not have seen them")
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
    by_relation = {r: t for r, t in g.relations.items() if t in g.seeds}
    for uid, src in (data.get("sources") or {}).items():
        rel = src.get("relation_name")
        if rel and rel in by_relation:  # a source that reads a seed (a package's integration tests)
            by_id[uid] = by_relation[rel]
            continue
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
    (dest / DEPS_FILE).write_text(json.dumps({m: sorted(d) for m, d in g.depends.items()}, indent=1) + "\n",
                                  encoding="utf-8")


def upstream(g: Graph, names: list[str]) -> set[str]:
    """The models the given models read, directly or not, and themselves."""
    seen, todo = set(), [n for n in names if n in g.models]
    while todo:
        m = todo.pop()
        if m not in seen:
            seen.add(m)
            todo += list(g.depends.get(m, ()))
    return seen


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
