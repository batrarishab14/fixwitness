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
import uuid
from dataclasses import dataclass, field
from pathlib import Path

SEED_ROWS = 200      # seeds are samples: the first rows are enough, and keep every case small
ORDER_FILE = "fixwitness_order.txt"
SEED_TYPES_FILE = "fixwitness_seed_types.json"  # beside manifest.json: the column types dbt gave each seed
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
    # The project's own dbt tests, as rules on the input tables: {"table", "columns", "test", "values",
    # "from"}. A generated input that breaks one is reviewed instead of failed: the project says such
    # data does not occur.
    contracts: list[dict] = field(default_factory=list)


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


ADAPTER_PIP = {"duckdb": "dbt-duckdb", "postgres": "dbt-postgres", "snowflake": "dbt-snowflake",
               "bigquery": "dbt-bigquery"}


def dbt_available(adapter: str = "duckdb") -> bool:
    try:
        found = importlib.util.find_spec(f"dbt.adapters.{adapter}") is not None
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


_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_CLOCK = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d+)?\s+")


def _clean(line: str) -> str:
    return _CLOCK.sub("", _ANSI.sub("", line)).rstrip()


def error_lines(output: str, limit: int = 4) -> list[str]:
    """dbt's own explanation of a failure: what follows "Completed with N errors" (the summary dbt
    prints at the end), else the first error line and the lines after it."""
    lines = [_clean(l) for l in output.splitlines()]
    lines = [l for l in lines if l.strip()]
    for i, l in enumerate(lines):
        if re.search(r"Completed with \d+ errors?", l):
            after = [x.strip() for x in lines[i + 1:] if not x.lstrip().startswith("Done.")]
            if after:
                return after[:limit]
    for i, l in enumerate(lines):
        if re.search(r"\b(Error|error|ERROR|Failure|exception)\b", l) and "ERROR=" not in l \
                and not l.lstrip().startswith(("Finished running", "Done.")):
            return [x.strip() for x in lines[i:i + limit]]
    return [x.strip() for x in lines[-limit:]]


def _run(args: list[str], project: Path, env: dict, timeout: int) -> None:
    try:
        proc = subprocess.run(args, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise DbtError(f"`{' '.join(args[:2])}` took longer than {timeout}s") from None
    if proc.returncode != 0:
        out = proc.stdout + proc.stderr
        why = " / ".join(error_lines(out)) or f"exit code {proc.returncode}"
        tail = "\n".join(_clean(l) for l in out.strip().splitlines()[-30:])
        raise DbtError(f"`{' '.join(args[:2])}` failed in {project.name}: {why}\n{tail}")


def _profile(path: Path, name: str, db: Path, schema: str) -> None:
    # The target is named after the adapter, as dbt packages' own CI names it: their configs test
    # target.name ("{{ 'varchar' if target.name == 'postgres' else 'string' }}") as well as target.type.
    path.write_text(
        f"{name}:\n  target: duckdb\n  outputs:\n    duckdb:\n      type: duckdb\n"
        f"      path: {json.dumps(str(db))}\n      schema: {json.dumps(schema)}\n      threads: 1\n",
        encoding="utf-8")


def _warehouse_profile(path: Path, name: str, url: str, schema: str) -> str:
    """A dbt profile for your warehouse, with a private schema. Secrets come from the environment
    variables the drivers read (never from the URL, which is recorded in the proof)."""
    from fixwitness.warehouse import parse_url
    i = parse_url(url)
    k, q = i["kind"], i["query"]
    env = lambda var: "\"{{ env_var('" + var + "', '') }}\""  # noqa: E731
    if k == "postgres":
        lines = ["type: postgres", f"host: {json.dumps(i['host'] or 'localhost')}", f"port: {i['port'] or 5432}",
                 f"user: {json.dumps(i['user'] or '')}", f"password: {env('PGPASSWORD')}",
                 f"dbname: {json.dumps(i['path'] or 'postgres')}", f"schema: {json.dumps(schema)}", "threads: 4"]
    elif k == "snowflake":
        lines = ["type: snowflake", f"account: {json.dumps(i['host'] or '')}", f"user: {json.dumps(i['user'] or '')}",
                 f"database: {json.dumps(i['path'] or '')}", f"warehouse: {json.dumps(q.get('warehouse') or '')}",
                 f"schema: {json.dumps(schema)}", "threads: 4"]
        if q.get("role"):
            lines.append(f"role: {json.dumps(q['role'])}")
        if os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"):
            lines += [f"private_key_path: {env('SNOWFLAKE_PRIVATE_KEY_PATH')}",
                      f"private_key_passphrase: {env('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')}"]
        elif os.environ.get("SNOWFLAKE_AUTHENTICATOR"):
            lines.append(f"authenticator: {env('SNOWFLAKE_AUTHENTICATOR')}")
        else:
            lines.append(f"password: {env('SNOWFLAKE_PASSWORD')}")
    else:
        keyfile = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        lines = ["type: bigquery", f"method: {'service-account' if keyfile else 'oauth'}",
                 f"project: {json.dumps(i['host'] or os.environ.get('GOOGLE_CLOUD_PROJECT', ''))}",
                 f"dataset: {json.dumps(schema)}", "threads: 4"]
        if keyfile:
            lines.append(f"keyfile: {env('GOOGLE_APPLICATION_CREDENTIALS')}")
        if q.get("location"):
            lines.append(f"location: {json.dumps(q['location'])}")
    body = "".join(f"      {l}\n" for l in lines)
    path.write_text(f"{name}:\n  target: {k}\n  outputs:\n    {k}:\n{body}", encoding="utf-8")
    return k


def schema_variable(project: Path, schema: str) -> str | None:
    """The variable in dbt_project.yml whose value is the schema the sources read (zendesk_schema:
    zendesk_integration_tests), so a private schema can be put in its place."""
    text = (project / "dbt_project.yml").read_text(encoding="utf-8")
    hits = re.findall(rf"^\s*([A-Za-z_][\w]*)\s*:\s*['\"]?{re.escape(schema)}['\"]?\s*(?:#.*)?$", text, re.M)
    hits = [h for h in hits if h not in ("schema", "+schema", "name", "profile")]
    return hits[0] if len(set(hits)) == 1 else None


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


PRIVATE_SCHEMA = "fw_compiled"  # how the private schema is named in compiled SQL kept by fixwitness
CACHE_ENV = "FIXWITNESS_CACHE_DIR"     # where compiled manifests are kept; "off" turns the cache off
_SKIP_DIRS = {".git", "target", "logs", "dbt_packages", "dbt_modules", "__pycache__", ".venv", "venv",
              "node_modules", ".fixwitness"}


def cache_dir() -> Path | None:
    where = os.environ.get(CACHE_ENV)
    if where and where.lower() in ("off", "0", "no", "false"):
        return None
    base = Path(where) if where else Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "fixwitness"
    return base / "dbt"


def tree_key(tree: Path, project: Path, warehouse: str | None) -> str:
    """What a compile depends on: every file of the tree (the project and the package it installs
    from ../), the project's place in it, the adapter, the warehouse and the dbt version."""
    import hashlib
    from importlib.metadata import PackageNotFoundError, version
    h = hashlib.sha256()
    for path in sorted(tree.rglob("*")):
        rel = path.relative_to(tree)
        if any(part in _SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        h.update(rel.as_posix().encode() + b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    try:
        dbt_version = version("dbt-core")
    except PackageNotFoundError:
        dbt_version = "?"
    h.update(f"\0{project.relative_to(tree).as_posix()}\0{warehouse or 'duckdb'}\0{dbt_version}".encode())
    for name in sorted(os.environ):  # env_var() in the project can read these (only their hash is kept)
        if name.startswith("DBT_") and name not in ("DBT_PROFILES_DIR", "DBT_TARGET_PATH", "DBT_LOG_PATH"):
            h.update(f"\0{name}={os.environ[name]}".encode())
    return h.hexdigest()[:32]


def compile_cached(tree: Path, project: Path, out: Path, notes: list[str] | None = None,
                   warehouse: str | None = None, timeout: int = 900) -> Path:
    """compile_project, reusing the manifest of an identical earlier compile (same files, adapter,
    warehouse and dbt version), so checking again after a small change rebuilds only what changed."""
    root = cache_dir()
    key = tree_key(tree, project, warehouse) if root is not None else None
    hit = root / key if root is not None else None
    if hit is not None and (hit / "manifest.json").is_file():
        (out / "target").mkdir(parents=True, exist_ok=True)
        for f in hit.iterdir():
            shutil.copy2(f, out / "target" / f.name)
        if notes is not None:
            notes.append(f"dbt: reused an identical earlier compile of {project.name} (cache {key[:12]}; "
                         f"set {CACHE_ENV}=off to rebuild)")
        return out / "target" / "manifest.json"
    manifest = compile_project(project, out, timeout, notes, warehouse)
    if hit is not None:
        try:
            tmp = hit.with_name(hit.name + f".tmp{os.getpid()}")
            tmp.mkdir(parents=True, exist_ok=True)
            for name in ("manifest.json", SEED_TYPES_FILE):
                if (manifest.parent / name).is_file():
                    shutil.copy2(manifest.parent / name, tmp / name)
            os.replace(tmp, hit)
        except OSError:
            shutil.rmtree(tmp, ignore_errors=True)  # another check stored it first, or the disk is full
    return manifest


def compile_project(project: Path, out: Path, timeout: int = 900, notes: list[str] | None = None,
                    warehouse: str | None = None) -> Path:
    """dbt seed, dbt run and dbt compile, in a private DuckDB file or, with a warehouse URL, in a
    private schema of your warehouse with its own dbt adapter (dropped afterwards); return the
    manifest path."""
    adapter = "duckdb"
    if warehouse:
        from fixwitness.warehouse import parse_url
        adapter = parse_url(warehouse)["kind"]
    if not dbt_available(adapter):
        raise DbtError(f"compiling a dbt project needs dbt-core and the {ADAPTER_PIP[adapter]} adapter: "
                       f"pip install dbt-core {ADAPTER_PIP[adapter]} (or pass --manifest and --base-manifest)")
    settings = project_settings(project)
    profile = settings.get("profile") or settings.get("name") or "default"
    out.mkdir(parents=True, exist_ok=True)
    profiles = out / "profiles"
    profiles.mkdir(exist_ok=True)
    db = out / "fixwitness.duckdb"
    schema = "fw_" + uuid.uuid4().hex[:10]
    if warehouse:
        _warehouse_profile(profiles / "profiles.yml", profile, warehouse, schema)
    else:
        _profile(profiles / "profiles.yml", profile, db, "main")
    env = dict(os.environ, DBT_PROFILES_DIR=str(profiles), DBT_SEND_ANONYMOUS_USAGE_STATS="false",
               DBT_TARGET_PATH=str(out / "target"), DBT_LOG_PATH=str(out / "logs"))
    common = ["--project-dir", str(project), "--profiles-dir", str(profiles), "--target", adapter]
    if ((project / "packages.yml").exists() or (project / "dependencies.yml").exists()) \
            and not (project / "dbt_packages").exists():
        _run(["dbt", "deps", *common], project, env, timeout)
    manifest = out / "target" / "manifest.json"
    try:
        if _has_seeds(project):
            # Sources that read the seeds through a schema variable: in DuckDB the target schema is
            # set to it; in a warehouse the variable is set to the private schema instead.
            _run(["dbt", "parse", *common], project, env, timeout)
            src = source_schema(manifest)
            if src and src != schema:
                if warehouse:
                    var = schema_variable(project, src)
                    if var is None:
                        raise DbtError(f"the sources read the seeds from schema {src}, which no variable in "
                                       f"{project.name}/dbt_project.yml sets, so they can't be pointed at a "
                                       f"private schema in your warehouse")
                    common += ["--vars", json.dumps({var: schema})]
                else:
                    _profile(profiles / "profiles.yml", profile, db, src)
            _run(["dbt", "seed", *common], project, env, timeout)
            if warehouse:
                write_warehouse_seed_types(warehouse, schema, manifest, out / "target" / SEED_TYPES_FILE)
            else:
                write_seed_types(db, manifest, out / "target" / SEED_TYPES_FILE)
            # Built once on the seeds, so macros that read a model's columns or query a model while
            # compiling see the real tables. A model that fails to build here is still compiled.
            try:
                _run(["dbt", "run", *common], project, env, timeout)
            except DbtError as exc:
                if notes is not None:
                    first = str(exc).splitlines()[0].split(": ", 1)[-1]
                    notes.append(f"dbt: `dbt run` on the seeds failed in {project.name} ({first.strip()[:200]}); "
                                 f"models were still compiled, but macros that read a model's columns may "
                                 f"not have seen them")
        _run(["dbt", "compile", *common], project, env, timeout)
    finally:
        if warehouse:
            from fixwitness.warehouse import drop_schemas
            try:
                drop_schemas(warehouse, schema)
            except Exception as exc:  # reported, never hidden: the schemas would be left behind
                if notes is not None:
                    notes.append(f"dbt: could not drop the private schemas {schema}*: {exc}")
    if not manifest.is_file():
        raise DbtError(f"dbt compile wrote no manifest for {project.name}")
    if warehouse:  # the private schema's name is random: the same name in both versions' SQL
        text = manifest.read_text(encoding="utf-8")
        manifest.write_text(text.replace(schema, PRIVATE_SCHEMA), encoding="utf-8")
    meta = out / "target" / SEED_TYPES_FILE
    if meta.is_file():  # the adapter the types come from, so they are used only in that database
        data = json.loads(meta.read_text(encoding="utf-8"))
        meta.write_text(json.dumps({"adapter": adapter, "types": data}, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    return manifest


def write_seed_types(db: Path, manifest: Path, dest: Path) -> None:
    """The column types dbt gave each seed in the DuckDB file (from column_types, or inferred by
    dbt), so the generated tables are loaded with the same types. Nothing is written if DuckDB's
    Python module is missing; the types are then inferred from the values."""
    try:
        import duckdb
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (ImportError, OSError, ValueError):
        return
    seeds = {}
    for n in (data.get("nodes") or {}).values():
        if n.get("resource_type") == "seed":
            seeds[(str(n.get("schema") or "").lower(), str(n.get("alias") or n["name"]).lower())] = n["name"]
    try:
        con = duckdb.connect(str(db), read_only=True)
        try:
            rows = con.execute("select table_schema, table_name, column_name, data_type from information_schema.columns "
                               "order by table_schema, table_name, ordinal_position").fetchall()
        finally:
            con.close()
    except Exception:
        return
    out: dict[str, dict[str, str]] = {}
    for schema, table, column, data_type in rows:
        name = seeds.get((str(schema).lower(), str(table).lower()))
        if name is not None:
            out.setdefault(name, {})[column] = data_type
    if out:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def write_warehouse_seed_types(url: str, schema: str, manifest: Path, dest: Path) -> None:
    """The column types your warehouse gave each seed (in the private schemas)."""
    from fixwitness.warehouse import columns
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        rows = columns(url, schema)
    except Exception:
        return
    seeds = {}
    for n in (data.get("nodes") or {}).values():
        if n.get("resource_type") == "seed":
            seeds[str(n.get("alias") or n["name"]).lower()] = n["name"]
    out: dict[str, dict[str, str]] = {}
    for _schema, table, column, data_type in rows:
        name = seeds.get(str(table).lower())
        if name is not None:
            out.setdefault(name, {})[column] = data_type
    if out:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def seed_types(manifest: Path) -> tuple[str | None, dict[str, dict[str, str]]]:
    """(adapter, {seed: {column: type}}) written beside a manifest fixwitness compiled."""
    f = manifest.parent / SEED_TYPES_FILE
    try:
        data = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    except (OSError, ValueError):
        return None, {}
    if "types" in data and "adapter" in data:
        return data["adapter"], data["types"]
    return "duckdb", data


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
    g.contracts = _contracts(nodes, by_id, g)
    return g


_TESTS = {"unique", "not_null", "accepted_values", "unique_combination_of_columns"}
# A model that does any of these can make a test true of its output and false of its input.
_CHANGES_ROWS = re.compile(r"\b(where|group\s+by|distinct|qualify|join|union|having|limit|row_number|rank|"
                           r"dense_rank|unnest|lateral|pivot|intersect|except)\b", re.I)
_SQL_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)


def _renamed_from(sql: str, column: str) -> str | None:
    """The column a model's SQL renames to `column` (`id as ticket_id`, `cast(id as bigint) as
    ticket_id`), or None."""
    col = re.escape(column)
    m = re.search(rf'(?:cast\s*\(\s*)?"?([A-Za-z_]\w*)"?(?:\s*(?:as|::)\s*[\w ]+?(?:\([\d,\s]*\))?\s*\)?)?'
                  rf'\s+as\s+"?{col}"?(?![\w"])', sql, re.I)
    return m.group(1) if m else None


def _contracts(nodes: dict, by_id: dict, g: Graph) -> list[dict]:
    """The project's unique, not_null, accepted_values and dbt_utils.unique_combination_of_columns
    tests, traced back to the input table column they are about: directly (a test on a seed or a
    source), or through a chain of models that each read one other model or table and rename the
    column at most (Fivetran-style staging: stg_x <- stg_x_tmp <- source)."""
    parents: dict[str, list[str]] = {}
    for uid, n in nodes.items():
        if n.get("resource_type") == "model" and uid in by_id:
            parents[by_id[uid]] = [by_id[d] for d in (n.get("depends_on") or {}).get("nodes", []) if d in by_id]
    headers: dict[str, list[str]] = {}

    def header(table: str) -> list[str]:
        if table not in headers:
            path = g.seeds.get(table)
            try:
                with path.open(encoding="utf-8-sig") as fh:
                    headers[table] = [c.strip() for c in fh.readline().strip().split(",")]
            except (OSError, AttributeError):
                headers[table] = []
        return headers[table]

    def passed_through(sql: str, col: str) -> str | None:
        """The parent's column that this model passes through unchanged as `col`, or None."""
        found = _renamed_from(sql, col)
        if found:
            return found
        q = re.escape(col)
        if re.search(rf'(?:\bselect\b|,)\s*(?:\w+\.)?"?{q}"?\s*(?=,|\bfrom\b)', sql, re.I) \
                or re.search(r"\bselect\s+\*\s+from\b", sql, re.I) and not re.search(rf"\bas\s+\"?{q}\"?(?![\w\"])", sql, re.I):
            return col
        return None

    def trace(name: str, cols: list[str]) -> tuple[str, list[str]] | None:
        for _ in range(6):
            if name in g.seeds or name in g.sources:
                have = {c.lower(): c for c in header(name)}
                if not have:
                    return None
                got = [have.get(c.lower()) for c in cols]
                return (name, got) if all(got) else None
            if name not in g.models or len(parents.get(name, [])) != 1:
                return None
            sql = _SQL_COMMENT.sub(" ", g.models[name])
            if _CHANGES_ROWS.search(sql):  # filters, joins, dedup: the test says nothing about the input
                return None
            cols = [passed_through(sql, c) for c in cols]
            if None in cols:
                return None
            name = parents[name][0]
        return None

    out, seen = [], set()
    for n in nodes.values():
        if n.get("resource_type") != "test":
            continue
        meta = n.get("test_metadata") or {}
        test, kwargs, config = meta.get("name"), meta.get("kwargs") or {}, n.get("config") or {}
        if test not in _TESTS or config.get("where") or config.get("enabled") is False:
            continue
        if test == "unique_combination_of_columns":
            cols = list(kwargs.get("combination_of_columns") or [])
        else:
            cols = [kwargs.get("column_name") or n.get("column_name")]
        if not cols or not all(isinstance(c, str) and re.fullmatch(r"[A-Za-z_]\w*", c) for c in cols):
            continue  # an expression, not a column
        attached = n.get("attached_node") or next(iter((n.get("depends_on") or {}).get("nodes", [])), None)
        if attached not in by_id:
            continue
        found = trace(by_id[attached], cols)
        if found is None:
            continue
        table, columns = found
        values = [str(v) for v in kwargs.get("values") or []] if test == "accepted_values" else None
        key = (table, tuple(columns), test, tuple(values or ()))
        if key in seen:
            continue
        seen.add(key)
        out.append({"table": table, "columns": columns, "test": "unique" if test.startswith("unique") else test,
                    "values": values, "from": f"{by_id[attached]}: {test}({', '.join(cols)})"})
    return out


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
