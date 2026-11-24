"""Work out what to compare and how to run it, so the user has to specify as little as possible.

* git mode   - the original comes from a git revision (default HEAD), the fix from the working
               tree. Both are full snapshots of the repository, so fixes that touch imported
               modules or config files are compared correctly.
* files mode - two explicit files, no git needed.

The run command and the sample file are detected when not given.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from fixwitness.cases import SampleError, parse_sample
from fixwitness.discover import table_bytes
from fixwitness.config import Config, ConfigError
from fixwitness.runner import Invocation, RunConfigError, Side, no_network_available, run_side
from fixwitness.sql import (SqlError, choose_engine, dependencies, find_models, make_bundle, make_outputs,
                            table_types)

INTERPRETERS = {
    ".py": "python3", ".sh": "bash", ".bash": "bash", ".js": "node", ".mjs": "node", ".cjs": "node",
    ".rb": "ruby", ".pl": "perl", ".r": "Rscript", ".php": "php",
}
CONVENTIONS = [
    "{prog} {script} {input} {output}",
    "{prog} {script} {input}",
    "{prog} {script} < {input}",
]
SAMPLE_DIRS = ["", "data", "sample", "samples", "fixtures", "testdata", "test_data", "tests/data", "tests/fixtures"]


class PlanError(ConfigError):
    pass


@dataclass
class Plan:
    mode: str
    before: Side
    after: Side
    invocation: Invocation
    sample_path: Path
    sample: bytes
    output: str
    work: Path
    canary_dir: Path
    incident_path: Path | None = None
    incident: bytes | None = None
    incident_expected: bytes | None = None
    after_invocation: Invocation | None = None   # set when the fix is run differently from the original
    sql: dict | None = None                       # SQL mode: tables, types, engine
    sample_format: str = "csv"                    # csv, json (JSON or JSON Lines) or parquet
    notes: list[str] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)      # what the proof hashes
    replay: dict = field(default_factory=dict)      # what replay needs
    _tmp: tempfile.TemporaryDirectory | None = None

    @property
    def fix_invocation(self) -> Invocation:
        return self.after_invocation or self.invocation

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    def __enter__(self) -> "Plan":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file, or a folder (every file's relative path and contents, in sorted order)."""
    if path.is_dir():
        h = hashlib.sha256()
        for f in sorted(p for p in path.rglob("*") if p.is_file()):
            name, data = f.relative_to(path).as_posix().encode(), f.read_bytes()
            h.update(len(name).to_bytes(8, "big") + name + len(data).to_bytes(8, "big") + data)
        return h.hexdigest()
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- git helpers

def _git(args: list[str], cwd: Path, binary: bool = False):
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=not binary)
    except FileNotFoundError as exc:
        raise PlanError("git is not installed; use --before/--after instead") from exc
    if proc.returncode != 0:
        err = proc.stderr if isinstance(proc.stderr, str) else proc.stderr.decode(errors="replace")
        raise PlanError(f"git {' '.join(args)} failed: {err.strip()}")
    return proc.stdout


def repo_root(start: Path) -> Path:
    try:
        return Path(_git(["rev-parse", "--show-toplevel"], start).strip())
    except PlanError as exc:
        raise PlanError(f"{start} is not inside a git repository; use --before and --after instead") from exc


def changed_files(root: Path, commit: str) -> list[tuple[str, str]]:
    """(status, path) for tracked changes against commit plus untracked, non-ignored files."""
    out = _git(["diff", "--name-status", "-z", "--no-renames", commit], root)
    tokens = [t for t in out.split("\0") if t]
    changes = [(tokens[i], tokens[i + 1]) for i in range(0, len(tokens) - 1, 2)]
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z"], root)
    changes += [("A", p) for p in untracked.split("\0") if p]
    changes = [c for c in changes if not c[1].startswith(".fixwitness/")]
    return sorted(set(changes), key=lambda x: x[1])


def export_commit(root: Path, commit: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(["git", "archive", "--format=tar", commit], cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            try:
                tar.extractall(dest, filter="data")
            except TypeError:  # Python without extraction filters
                tar.extractall(dest)
        err = proc.stderr.read().decode(errors="replace").strip()
    finally:
        proc.stdout.close()
        proc.stderr.close()
    if proc.wait() != 0:
        raise PlanError(f"git archive {commit} failed: {err}")


def snapshot_worktree(root: Path, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    listing = _git(["ls-files", "-z", "--cached", "--others", "--exclude-standard"], root)
    count = 0
    for rel in sorted(set(p for p in listing.split("\0") if p)):
        src = root / rel
        if not (src.is_file() or src.is_symlink()):
            continue  # deleted in the working tree, or a submodule
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            os.symlink(os.readlink(src), target)
        else:
            shutil.copy2(src, target)
        count += 1
    return count


# ---------------------------------------------------------------- detection

def program_for(script: Path) -> str | None:
    prog = INTERPRETERS.get(script.suffix.lower())
    if prog:
        return prog
    try:
        first = script.read_bytes()[:200].split(b"\n", 1)[0].decode("utf-8", errors="replace")
    except OSError:
        return None
    if first.startswith("#!"):
        parts = first[2:].strip().split()
        if parts and os.path.basename(parts[0]) == "env":
            parts = [p for p in parts[1:] if not p.startswith("-")]
        if parts:
            return os.path.basename(parts[0])
    return None


SAMPLE_PATTERNS = ("*.csv", "*.jsonl", "*.ndjson", "*.parquet", "*.json")
_FORMAT_HINTS = {".csv": re.compile(r"\bcsv\b|read_csv", re.I),
                 ".jsonl": re.compile(r"\bjson\b|jsonl|ndjson|read_json", re.I),
                 ".ndjson": re.compile(r"\bjson\b|jsonl|ndjson|read_json", re.I),
                 ".json": re.compile(r"\bjson\b|read_json", re.I),
                 ".parquet": re.compile(r"parquet|pyarrow", re.I)}


def discover_sample(near: Path, extra_roots: list[Path], script: Path | None = None) -> Path:
    """The sample input near the code: CSV, JSON Lines, Parquet or JSON.

    With several candidates, the script decides: a file it names, a file named like it
    (events.py -> events.jsonl), or the only file of the format it reads.
    """
    found: list[Path] = []
    for root in [near, *extra_roots]:
        for sub in SAMPLE_DIRS:
            d = root / sub if sub else root
            if d.is_dir():
                found += sorted(p for pat in SAMPLE_PATTERNS for p in d.glob(pat) if p.is_file()
                                and not (pat == "*.json" and p.name in ("package.json", "tsconfig.json")))
    unique = list(dict.fromkeys(p.resolve() for p in found))
    if script is not None and len(unique) > 1:
        source = script.read_text(encoding="utf-8", errors="replace") if script.is_file() else ""
        for pick in (lambda p: p.name in source, lambda p: p.stem.lower() == script.stem.lower()):
            hits = [p for p in unique if pick(p)]
            if len(hits) == 1:
                return hits[0]
        hinted = [p for p in unique if _FORMAT_HINTS.get(p.suffix.lower(), re.compile("$^")).search(source)]
        if len({p.suffix.lower() for p in hinted}) >= 1:
            fmt = [p for p in hinted if p.suffix.lower() != ".json"] or hinted
            if len(fmt) == 1:
                return fmt[0]
    csvs = [p for p in unique if p.suffix.lower() == ".csv"]
    if len(unique) == 1 or len(csvs) == 1:
        return (unique if len(unique) == 1 else csvs)[0]
    if not unique:
        raise PlanError(f"no sample input (CSV, JSON Lines or Parquet) found near {near}; pass one with --sample")
    listing = "\n".join(f"  {p}" for p in unique[:10])
    raise PlanError(f"several files could be the sample; pick one with --sample:\n{listing}")


def detect_run(work: Path, side: Side, prog: str, sample: bytes, base_inv: Invocation) -> tuple[str, list[str]]:
    """Try the common calling conventions on the original and return the first that works."""
    attempts = []
    probe_dir = work / "probe"
    for convention in CONVENTIONS:
        template = convention.replace("{prog}", prog)
        inv = Invocation(template=template, timeout=base_inv.timeout, allow_any=base_inv.allow_any,
                         pass_env=base_inv.pass_env, no_network=base_inv.no_network,
                         input_suffix=base_inv.input_suffix, output_suffix=base_inv.output_suffix)
        result = run_side(inv, side, probe_dir, sample)
        if result.ok and result.output:
            shutil.rmtree(probe_dir, ignore_errors=True)
            return template, attempts
        why = "timed out" if result.timed_out else (result.error or (result.stderr.decode(errors="replace").strip()[-200:]
                                                                      or "no output"))
        attempts.append(f"{template}: {why}")
    shutil.rmtree(probe_dir, ignore_errors=True)
    raise PlanError("could not work out how to run the original. Tried:\n  " + "\n  ".join(attempts)
                    + "\nPass the command with --run, e.g. --run 'python3 {script} {input} {output}'")


# ---------------------------------------------------------------- SQL and dbt models

_TABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def is_model_folder(p: Path | None) -> bool:
    return p is not None and p.is_dir() and any(p.rglob("*.sql"))


def is_sql(cfg: Config, *scripts: Path | None) -> bool:
    """SQL mode: the scripts are .sql files or folders of models (or tables are given), and no run
    command overrides it."""
    if cfg.run or cfg.command or cfg.function:
        return False
    return bool(cfg.tables) or any(p is not None and (p.suffix.lower() == ".sql" or is_model_folder(p))
                                   for p in scripts)


def _roots_near(target: Path, extra: list[Path]) -> list[Path]:
    """Where data files are looked for: the code's folder and each parent up to the last extra root."""
    start = target if target.is_dir() else target.parent
    roots = [start, *start.parents[:3], *extra]
    return list(dict.fromkeys(roots))


def is_frame(cfg: Config, *scripts: Path | None) -> bool:
    """DataFrame mode: a function to call is named, the scripts are Python, and no run command overrides it."""
    return bool(cfg.function) and not (cfg.run or cfg.command) and all(
        p is None or p.suffix.lower() == ".py" for p in scripts)


def _pipeline_outputs(cfg: Config, folder: Path, tables: set[str], notes: list[str]) -> list[str]:
    """The models to compare: those named, or the original's final models (no other model reads them)."""
    try:
        models = {name: p.read_text(encoding="utf-8") for name, p in find_models(folder).items()}
    except SqlError as exc:
        raise PlanError(str(exc)) from exc
    if not models:
        raise PlanError(f"no .sql models in {folder}")
    if cfg.sql_outputs and cfg.sql_outputs != ["all"]:
        unknown = [o for o in cfg.sql_outputs if o not in models]
        if unknown:
            raise PlanError(f"output model(s) {', '.join(unknown)} are not in the original's models "
                            f"({', '.join(sorted(models))})")
        return list(cfg.sql_outputs)
    if cfg.sql_outputs == ["all"]:
        notes.append(f"comparing every model: {', '.join(sorted(models))}")
        return sorted(models)
    read = set()
    for name, raw in models.items():
        read |= dependencies(raw, set(models) | tables, name)
    final = sorted(set(models) - read)
    notes.append(f"pipeline: {len(models)} models; comparing the final one{'s' if len(final) != 1 else ''} "
                 f"({', '.join(final)}), which no other model reads (set sql_outputs to compare others)")
    return final


def _read_tables(cfg: Config, spec: dict[str, str], what: str) -> tuple[dict[str, Path], dict[str, bytes]]:
    paths, data = {}, {}
    for name, value in spec.items():
        if not _TABLE_NAME.fullmatch(name):
            raise PlanError(f"{what} name {name!r} must be a plain SQL identifier (letters, digits, _)")
        p = cfg.resolve(value)
        if not p.is_file():
            raise PlanError(f"{what} {name}: file not found: {p}")
        try:
            raw = table_bytes(p)  # CSV as it is; Parquet and JSON Lines converted to CSV
            parse_sample(raw)
        except (SampleError, ValueError) as exc:
            raise PlanError(f"{what} {name} ({p.name}): {exc}") from exc
        paths[name], data[name] = p.resolve(), raw
    return paths, data


def _side_path(side: Side) -> Path:
    return (side.root / side.script) if side.root is not None else side.script


def tables_needed(cfg: Config, side: Side) -> list[str]:
    """The tables the original reads: a function's required parameters, or a query's FROM/JOIN tables."""
    from fixwitness.discover import _functions, query_tables, required_params
    src = _side_path(side)
    if cfg.function:
        fn = _functions(src.read_text(encoding="utf-8")).get(cfg.function)
        if fn is None:
            raise PlanError(f"{src.name} has no top-level function {cfg.function}()")
        return required_params(fn)
    if src.is_dir():
        models = {p.stem for p in src.rglob("*.sql")}
        names = [t for p in sorted(src.rglob("*.sql")) for t in query_tables(p.read_text(encoding="utf-8"))]
        return list(dict.fromkeys(t for t in names if t not in models))
    return query_tables(src.read_text(encoding="utf-8"))


def _discover_tables(cfg: Config, side: Side, roots: list[Path], notes: list[str]) -> dict[str, str]:
    from fixwitness.discover import match_tables
    names = tables_needed(cfg, side)
    if not names:
        raise PlanError("could not tell which tables the code reads; pass --table NAME=FILE.csv for each")
    found, missing = match_tables(names, roots)
    if missing:
        what = "parameter" if cfg.function else "table"
        raise PlanError(f"no data file found for {what}(s) {', '.join(missing)}: put a sample named after each "
                        f"(for example data/{missing[0]}.csv, .parquet or .jsonl) next to the code, in data/ or "
                        f"seeds/, or pass --table {missing[0]}=FILE")
    notes.append("tables found by name: " + ", ".join(f"{n} = {p.name}" for n, p in found.items()))
    return {n: str(p) for n, p in found.items()}


def _build_tables(cfg: Config, work: Path, canary_dir: Path, mode: str, side_b: Side, side_a: Side,
               inputs: dict, replay: dict, notes: list[str], folder: Path | None = None,
               search_roots: list[Path] | None = None) -> Plan:
    if cfg.tables:
        spec = dict(cfg.tables)
    elif cfg.sample:
        stem = cfg.resolve(cfg.sample).stem
        spec = {stem: cfg.sample}
        notes.append(f"table: {stem} (named after the sample file)")
    else:
        spec = _discover_tables(cfg, side_b, search_roots or [cfg.base_dir], notes)
    paths, tables = _read_tables(cfg, spec, "table")
    types = {name: table_types(raw) for name, raw in tables.items()}
    if cfg.function:
        return _finish_frame(cfg, work, canary_dir, mode, side_b, side_a, inputs, replay, notes, paths, tables, types)
    wh_env, wh_pass = {}, []
    if cfg.warehouse:
        from fixwitness.warehouse import SECRET_ENV, URL_ENV, WarehouseError, check_url
        try:
            kind = check_url(cfg.warehouse)
        except WarehouseError as exc:
            raise PlanError(str(exc)) from exc
        engine = "warehouse"
        wh_env, wh_pass = {URL_ENV: cfg.warehouse}, SECRET_ENV[kind]
        notes.append(f"SQL runs in your {kind} warehouse ({cfg.warehouse}): each run gets its own schema, "
                     f"dropped after it; the SQL runs as written")
    else:
        try:
            engine = choose_engine(cfg.engine)
        except SqlError as exc:
            raise PlanError(str(exc)) from exc
        notes.append(f"SQL engine: {engine}" + ("" if engine == "duckdb" or cfg.dialect else
                                                 " (install duckdb to check with DuckDB's SQL dialect)"))
    if cfg.dialect and engine != "warehouse":
        try:
            import sqlglot  # noqa: F401
        except ImportError:
            raise PlanError(f"dialect = {cfg.dialect} needs sqlglot to translate the SQL: pip install sqlglot") from None
        from sqlglot.dialects.dialect import Dialect
        try:
            Dialect.get_or_raise(cfg.dialect)
        except ValueError as exc:
            raise PlanError(f"unknown SQL dialect {cfg.dialect!r}: {exc}") from None
        notes.append(f"SQL written for {cfg.dialect}, translated to {engine} with sqlglot")
    outputs = None
    if folder is not None:
        outputs = _pipeline_outputs(cfg, folder, set(spec), notes)
    template = (f"{shlex.quote(sys.executable)} -m fixwitness.sqlrun --engine {engine} --dbt {cfg.dbt}"
                + (f" --dialect {cfg.dialect}" if cfg.dialect else "")
                + (f" --outputs {','.join(outputs)}" if outputs else "")
                + (" --ordered" if cfg.sql_ordered else "") + " {script} {input} {output}")
    inv = Invocation(template=template, timeout=max(cfg.timeout, 120) if wh_env else cfg.timeout,
                     allow_any=cfg.allow_any_command, pass_env=list(cfg.pass_env) + wh_pass,
                     no_network=cfg.no_network and not wh_env, input_suffix=".json",
                     output_suffix=".csv", require_script=True,
                     env={"PYTHONPATH": str(Path(__file__).resolve().parent.parent), **wh_env})
    first = next(iter(paths.values()))
    plan = Plan(mode=mode, before=side_b, after=side_a, invocation=inv, sample_path=first,
                sample=make_bundle(tables, types), output="csv", work=work, canary_dir=canary_dir, notes=notes,
                inputs=inputs | {"tables": {n: {"name": p.name, "sha256": sha256_file(p)}
                                            for n, p in paths.items()}, "engine": engine},
                replay=replay | {"tables": {n: str(p) for n, p in paths.items()}, "run": template})
    plan.sql = {"tables": tables, "types": types, "engine": engine, "incident_tables": {}, "outputs": outputs}
    return _with_tables_incident(cfg, plan, tables, types, outputs)


def _finish_frame(cfg: Config, work: Path, canary_dir: Path, mode: str, side_b: Side, side_a: Side,
                  inputs: dict, replay: dict, notes: list[str], paths: dict[str, Path],
                  tables: dict[str, bytes], types: dict) -> Plan:
    """A Python function over DataFrames: the same generated tables as SQL mode, called through pyrun."""
    from fixwitness.pyrun import detect_library
    libs = []
    for side in (side_b, side_a):
        src = (side.root / side.script) if side.root is not None else side.script
        lib = detect_library(src.read_text(encoding="utf-8")) if cfg.library == "auto" else cfg.library
        try:
            __import__(lib)
        except ImportError:
            raise PlanError(f"the {side.label} uses {lib}, which is not installed here (pip install {lib})") from None
        libs.append(lib)
    notes.append(f"DataFrame function {cfg.function}(): "
                 + (f"{libs[0]}" if libs[0] == libs[1] else f"original uses {libs[0]}, fix uses {libs[1]}")
                 + "; tables loaded with the sample's column types")
    engine = libs[0] if libs[0] == libs[1] else f"{libs[0]} -> {libs[1]}"
    template = (f"{shlex.quote(sys.executable)} -m fixwitness.pyrun --function {cfg.function} --library {cfg.library}"
                + (" --ordered" if cfg.sql_ordered else "") + " {script} {input} {output}")
    inv = Invocation(template=template, timeout=cfg.timeout, allow_any=cfg.allow_any_command,
                     pass_env=cfg.pass_env, no_network=cfg.no_network, input_suffix=".json",
                     output_suffix=".csv", require_script=True,
                     env={"PYTHONPATH": str(Path(__file__).resolve().parent.parent)})
    plan = Plan(mode=mode, before=side_b, after=side_a, invocation=inv, sample_path=next(iter(paths.values())),
                sample=make_bundle(tables, types), output="csv", work=work, canary_dir=canary_dir, notes=notes,
                inputs=inputs | {"tables": {n: {"name": p.name, "sha256": sha256_file(p)}
                                            for n, p in paths.items()}, "engine": engine},
                replay=replay | {"tables": {n: str(p) for n, p in paths.items()}, "run": template})
    plan.sql = {"tables": tables, "types": types, "engine": engine, "incident_tables": {}, "outputs": None,
                "function": cfg.function, "libraries": libs}
    return _with_tables_incident(cfg, plan, tables, types, None)


def _with_tables_incident(cfg: Config, plan: Plan, tables: dict[str, bytes], types: dict,
                          outputs: list[str] | None) -> Plan:

    inc_spec = dict(cfg.incident_tables or {})
    if not inc_spec and cfg.incident:
        if len(tables) != 1:
            raise PlanError("with several tables, give the incident as incident_tables "
                            "(--incident-table NAME=FILE.csv)")
        inc_spec = {next(iter(tables)): cfg.incident}
    if inc_spec:
        unknown = sorted(set(inc_spec) - set(tables))
        if unknown:
            raise PlanError(f"incident table(s) {', '.join(unknown)} are not among the tables ({', '.join(tables)})")
        inc_paths, inc_data = _read_tables(cfg, inc_spec, "incident table")
        plan.sql["incident_tables"] = inc_data
        plan.incident = make_bundle({**tables, **inc_data}, types)
        plan.incident_path = next(iter(inc_paths.values()))
        plan.inputs["incident_tables"] = {n: {"name": p.name, "sha256": sha256_file(p)}
                                          for n, p in inc_paths.items()}
        plan.replay["incident_tables"] = {n: str(p) for n, p in inc_paths.items()}
    if cfg.incident_expected:
        if not inc_spec:
            raise PlanError("--incident-expected needs an incident (--incident-table NAME=FILE.csv)")
        p = cfg.resolve(cfg.incident_expected)
        if not p.is_file():
            raise PlanError(f"expected-output file not found: {p}")
        plan.incident_expected = p.read_bytes()
        plan.inputs["incident_expected"] = {"name": p.name, "sha256": sha256_bytes(plan.incident_expected)}
        plan.replay["incident_expected"] = str(p.resolve())
        if outputs is not None:
            if len(outputs) != 1:
                raise PlanError(f"the expected output is one CSV, but {len(outputs)} models are compared "
                                f"({', '.join(outputs)}); name the model it is for with sql_outputs")
            plan.incident_expected = make_outputs({outputs[0]: plan.incident_expected})
    return plan


# ---------------------------------------------------------------- dbt projects

def dbt_project_for(cfg: Config, target: Path | None, root: Path) -> Path | None:
    """The dbt project a target is in, when the project should be compiled by dbt itself."""
    from fixwitness.dbtmode import find_project
    if cfg.dbt == "off" or cfg.run or cfg.command or cfg.function or target is None:
        return None
    if target.is_file() and target.suffix.lower() not in (".sql", ".yml", ".yaml", ".csv"):
        return None
    return find_project(target, root)


def _build_dbt(cfg: Config, work: Path, canary_dir: Path, mode: str, manifests: tuple[Path, Path],
               projects: tuple[Path | None, Path | None], inputs: dict, replay: dict, notes: list[str],
               search_roots: list[Path]) -> Plan:
    from fixwitness.dbtmode import (DbtError, changed_models, final_downstream, read_manifest, seed_sample,
                                    write_models)
    try:
        g0, g1 = read_manifest(manifests[0], projects[0]), read_manifest(manifests[1], projects[1])
    except (DbtError, OSError, ValueError, KeyError) as exc:
        raise PlanError(f"could not read the dbt manifest: {exc}") from exc
    changed = changed_models(g0, g1)
    if not changed:
        raise PlanError("no dbt model's compiled SQL changed between the two versions")
    outputs = list(cfg.sql_outputs) if cfg.sql_outputs and cfg.sql_outputs != ["all"] else (
        sorted(g0.models) if cfg.sql_outputs == ["all"] else final_downstream(g0, changed))
    if not outputs:
        raise PlanError(f"the changed models ({', '.join(changed)}) are new: there is no original to compare")
    notes.append(f"dbt: {len(g0.models)} models; compiled SQL changed in {', '.join(changed)}; comparing "
                 f"{', '.join(outputs)} (the final models downstream of the change)")
    for skipped in sorted(set(g0.skipped) | set(g1.skipped)):
        notes.append(f"dbt: not run: {skipped}")
    # Tables: the seeds (cut to their first rows), and a sample for each source.
    spec: dict[str, str] = {}
    for name, path in {**g0.seeds, **g1.seeds}.items():
        if path.is_file():
            spec[name] = str(seed_sample(path, work / "dbt" / "seeds" / f"{name}.csv"))
    sources = {**g0.sources, **g1.sources}
    given = dict(cfg.tables or {})
    wanted = sorted({t for g in (g0, g1) for m in g.models for t in sources if f'"{t}"' in _bare_models(g)[m]})
    missing = []
    for table in wanted:
        src, name = sources[table]
        hit = given.get(table) or given.get(f"{src}.{name}") or given.get(name)
        if hit is None:
            from fixwitness.discover import match_tables
            found, _ = match_tables([name], search_roots)
            hit = str(found[name]) if name in found else None
        if hit is None:
            missing.append(f"{src}.{name}")
        else:
            spec[table] = hit
    if missing:
        raise PlanError(f"no sample for the dbt source(s) {', '.join(missing)}: put a CSV named after each "
                        f"table in the project's seeds/ or data/ folder, or pass --table {missing[0].split('.')[-1]}=FILE")
    if not spec:
        raise PlanError("the project has no seeds and no sources with a sample: nothing to load")
    d0, d1 = work / "dbt" / "original", work / "dbt" / "fix"
    write_models(g0, d0)
    write_models(g1, d1)
    engine, dialect = cfg.engine, cfg.dialect
    if g0.adapter != "duckdb" and not dialect:
        dialect = g0.adapter  # compiled for the warehouse: translated with sqlglot
    sub = dataclasses.replace(cfg, tables=spec, sql_outputs=outputs, dbt="off", engine=engine, dialect=dialect)
    plan = _build_tables(sub, work, canary_dir, mode, Side("original", None, d0), Side("fix", None, d1),
                         inputs | {"dbt": {"changed_models": changed, "compared": outputs, "adapter": g0.adapter}},
                         replay, notes, d0, search_roots)
    plan.replay.pop("tables", None)  # the tables are rebuilt from the project on replay
    plan.replay.pop("incident_tables", None) if not cfg.incident_tables else None
    plan.replay["dbt_project"] = True
    plan.replay["dbt_tables"] = {k: str(cfg.resolve(v)) for k, v in (cfg.tables or {}).items()} or None
    return plan


def _bare_models(g) -> dict[str, str]:
    from fixwitness.dbtmode import bare_sql
    return {m: bare_sql(g, m) for m in g.models}


def _compile_both(t0_project: Path, t1_project: Path, work: Path, notes: list[str]) -> tuple[Path, Path]:
    from fixwitness.dbtmode import DbtError, compile_project
    try:
        m0 = compile_project(t0_project, work / "dbt" / "build0")
        m1 = compile_project(t1_project, work / "dbt" / "build1")
    except DbtError as exc:
        raise PlanError(str(exc)) from exc
    notes.append("dbt: both versions compiled by dbt (dbt-duckdb adapter), so macros and packages are rendered by dbt")
    return m0, m1


# ---------------------------------------------------------------- build

def build_plan(cfg: Config) -> Plan:
    cfg.require_target()
    mode = cfg.mode()
    tmp = tempfile.TemporaryDirectory(prefix="fixwitness-")
    work = Path(tmp.name)
    canary_dir = work / "canaries"
    canary_dir.mkdir()
    try:
        if cfg.no_network and not no_network_available():
            raise PlanError("--no-network needs Linux with unprivileged user namespaces ('unshare -rn' failed)")
        plan = _build_git(cfg, work, canary_dir) if mode == "git" else _build_files(cfg, work, canary_dir)
        plan._tmp = tmp
        return plan
    except BaseException:
        tmp.cleanup()
        raise


def _load_incident(cfg: Config) -> tuple[Path | None, bytes | None]:
    if not cfg.incident:
        return None, None
    p = cfg.resolve(cfg.incident)
    if not p.is_file():
        raise PlanError(f"incident file not found: {p}")
    return p.resolve(), p.read_bytes()


def _with_incident(plan: "Plan", path: Path | None, data: bytes | None, cfg: Config | None = None) -> "Plan":
    if path is not None:
        plan.incident_path, plan.incident = path, data
        plan.inputs["incident"] = {"name": path.name, "sha256": sha256_bytes(data)}
        plan.replay["incident"] = str(path)
    if cfg is not None and cfg.incident_expected:
        if path is None:
            raise PlanError("--incident-expected needs --incident")
        p = cfg.resolve(cfg.incident_expected)
        if not p.is_file():
            raise PlanError(f"expected-output file not found: {p}")
        plan.incident_expected = p.read_bytes()
        plan.inputs["incident_expected"] = {"name": p.name, "sha256": sha256_bytes(plan.incident_expected)}
        plan.replay["incident_expected"] = str(p.resolve())
    return plan


def _output_suffix(output: str, fmt: str, cfg: Config, input_suffix: str) -> str:
    """The name of the output file the program is given: what a program of this kind writes."""
    if fmt in ("parquet", "json") and not cfg.output:
        return input_suffix  # JSON Lines in, JSON Lines out; Parquet in, Parquet out
    return {"csv": ".csv", "json": ".json"}.get(output, ".txt")


def _base_invocation(cfg: Config, sample_path: Path, template: str | None, require_script: bool) -> Invocation:
    output = cfg.output or "csv"
    return Invocation(template=template or "", timeout=cfg.timeout, allow_any=cfg.allow_any_command,
                      pass_env=cfg.pass_env, no_network=cfg.no_network,
                      input_suffix=sample_path.suffix or ".csv",
                      output_suffix=".csv" if output == "csv" else ".txt", require_script=require_script)


def sample_format(path: Path, data: bytes) -> str:
    """csv, json or parquet; the sample is checked so a bad one fails here, not on every case."""
    from fixwitness.formats import is_json_name, is_parquet, parse_json_sample, parquet_table
    try:
        if is_parquet(data):
            parquet_table(data)
            return "parquet"
        if is_json_name(path.name) or data.lstrip()[:1] in (b"[", b"{"):
            parse_json_sample(data)
            return "json"
    except SampleError as exc:
        raise PlanError(f"sample {path.name}: {exc}") from exc
    except Exception as exc:  # pyarrow could not read it
        raise PlanError(f"sample {path.name} is not a readable Parquet file: {exc}") from exc
    return "csv"


def _finish(cfg: Config, inv: Invocation, plan_notes: list[str], fmt: str = "csv") -> str:
    """Pick the comparison mode once the run command is known."""
    if cfg.output:
        return cfg.output
    if fmt == "json":
        plan_notes.append("outputs are compared as JSON when they parse as JSON (or JSON Lines), else as CSV")
        return "json"
    if fmt == "parquet":
        plan_notes.append("Parquet outputs are compared by value (read with pyarrow); other outputs as CSV")
        return "csv"
    if "{output}" in inv.template and inv.input_suffix.lower() == ".csv":
        return "csv"
    if inv.input_suffix.lower() == ".csv":
        plan_notes.append("output is standard output; it is compared as CSV if it parses, else as text")
        return "csv"
    return "text"


def _build_files(cfg: Config, work: Path, canary_dir: Path) -> Plan:
    if cfg.manifest and cfg.base_manifest and not (cfg.before or cfg.after):
        m0, m1 = cfg.resolve(cfg.base_manifest), cfg.resolve(cfg.manifest)
        for p in (m0, m1):
            if not p.is_file():
                raise PlanError(f"manifest not found: {p}")
        project = cfg.base_dir if (cfg.base_dir / "dbt_project.yml").is_file() else None
        return _build_dbt(cfg, work, canary_dir, "files", (m0, m1), (project, project),
                          {"mode": "files", "base_manifest": {"name": m0.name, "sha256": sha256_file(m0)},
                           "manifest": {"name": m1.name, "sha256": sha256_file(m1)}},
                          {"mode": "files", "base_manifest": str(m0.resolve()), "manifest": str(m1.resolve())},
                          [], [cfg.base_dir, *(cfg.base_dir / d for d in ("seeds", "data"))])
    before, after = cfg.resolve(cfg.before), cfg.resolve(cfg.after)
    for label, p in (("before", before), ("after", after)):
        if not p.exists():
            raise PlanError(f"{label} file not found: {p}")
    if before.is_dir() != after.is_dir():
        raise PlanError("compare a file with a file, or a folder of models with a folder of models")
    if before.is_dir() and not (is_model_folder(before) and is_sql(cfg, before)):
        raise PlanError(f"{before} is a folder; folders are compared as SQL/dbt models and it has no .sql files")
    notes: list[str] = []
    if is_sql(cfg, before, after) or is_frame(cfg, before, after):
        return _build_tables(
            cfg, work, canary_dir, "files", Side("original", None, before.resolve()), Side("fix", None, after.resolve()),
            {"mode": "files", "before": {"name": before.name, "sha256": sha256_file(before)},
             "after": {"name": after.name, "sha256": sha256_file(after)}},
            {"mode": "files", "before": str(before.resolve()), "after": str(after.resolve())}, notes,
            before.resolve() if before.is_dir() else None,
            _roots_near(after.resolve(), [before.resolve().parent, cfg.base_dir]))
    if cfg.sample:
        sample_path = cfg.resolve(cfg.sample)
    else:
        sample_path = discover_sample(after.parent, [before.parent], after)
        notes.append(f"sample: found {sample_path.name} next to the script")
    if not sample_path.is_file():
        raise PlanError(f"sample file not found: {sample_path}")
    sample = sample_path.read_bytes()
    fmt = sample_format(sample_path, sample)
    side_b = Side("original", None, before.resolve())
    side_a = Side("fix", None, after.resolve())
    inv = _base_invocation(cfg, sample_path, cfg.run, True)
    prog_b, prog_a = program_for(before), program_for(after)
    if not cfg.run:
        prog = prog_b or prog_a
        if not prog:
            raise PlanError(f"cannot tell how to run {before.name}; pass --run, e.g. --run 'python3 {{script}} {{input}}'")
        inv.template, _ = detect_run(work, side_b, prog, sample, inv)
        notes.append(f"run command: detected '{inv.template}'")
    inv_a = None
    if cfg.run_after or (not cfg.run and prog_a and prog_b and prog_a != prog_b):
        inv_a = dataclasses.replace(inv, template=cfg.run_after or "")
        if not cfg.run_after:  # e.g. a shell script rewritten in Python
            inv_a.template, _ = detect_run(work, side_a, prog_a, sample, inv_a)
            notes.append(f"fix run command: detected '{inv_a.template}'")
    output = _finish(cfg, inv, notes, fmt)
    inv.output_suffix = _output_suffix(output, fmt, cfg, inv.input_suffix)
    if inv_a is not None:
        inv_a.output_suffix = inv.output_suffix
    plan = _with_incident(Plan(
        mode="files", before=side_b, after=side_a, invocation=inv, sample_path=sample_path.resolve(),
        sample=sample, output=output, work=work, canary_dir=canary_dir, notes=notes,
        inputs={"mode": "files",
                "before": {"name": before.name, "sha256": sha256_file(before)},
                "after": {"name": after.name, "sha256": sha256_file(after)},
                "sample": {"name": sample_path.name, "sha256": sha256_bytes(sample)}},
        replay={"mode": "files", "before": str(before.resolve()), "after": str(after.resolve()),
                "sample": str(sample_path.resolve()), "run": inv.template,
                "run_after": inv_a.template if inv_a else None},
    ), *_load_incident(cfg), cfg)
    plan.after_invocation = inv_a
    plan.sample_format = fmt
    return plan


def _build_git(cfg: Config, work: Path, canary_dir: Path) -> Plan:
    target_abs = cfg.resolve(cfg.path) if cfg.path else None
    if target_abs is not None and not target_abs.exists():
        raise PlanError(f"file not found: {target_abs}")
    if target_abs is not None and target_abs.is_dir() and not is_model_folder(target_abs):
        raise PlanError(f"{target_abs} is a folder; folders are compared as SQL/dbt models and it has no .sql files")
    anchor = target_abs if target_abs is not None and target_abs.is_dir() else (
        target_abs.parent if target_abs is not None else cfg.base_dir)
    root = repo_root(anchor)
    commit = _git(["rev-parse", "--verify", f"{cfg.base}^{{commit}}"], root).strip()
    changes = changed_files(root, commit)
    if not changes:
        raise PlanError(f"nothing to compare: the working tree has no changes against {cfg.base} ({commit[:12]})")
    notes = [f"original: {cfg.base} ({commit[:12]}); fix: your working tree "
             f"({len(changes)} changed file{'s' if len(changes) != 1 else ''})"]
    rel = None
    if target_abs is not None:
        rel = target_abs.resolve().relative_to(root.resolve()).as_posix()
        inside = (lambda p: True) if rel == "." else (lambda p: p == rel or p.startswith(rel + "/"))
        if not any(inside(p) for _, p in changes):
            notes.append(f"{rel} itself is unchanged; comparing because other files changed")

    t0, t1 = work / "trees" / "t0", work / "trees" / "t1"
    export_commit(root, commit, t0)
    snapshot_worktree(root, t1)
    project = dbt_project_for(cfg, target_abs, root) if target_abs is not None else None
    if project is not None:
        from fixwitness.dbtmode import dbt_available
        prel = project.resolve().relative_to(root.resolve()).as_posix()
        if cfg.manifest and cfg.base_manifest:
            m0, m1 = cfg.resolve(cfg.base_manifest), cfg.resolve(cfg.manifest)
        elif dbt_available():
            m0, m1 = _compile_both(t0 / prel, t1 / prel, work, notes)
        else:
            m0 = m1 = None
            notes.append("dbt: dbt-core and dbt-duckdb are not installed, so models are rendered by fixwitness "
                         "(ref, source and config only); install them to check projects that use macros")
        if m0 is not None:
            changed = [{"path": p, "status": st, "sha256": sha256_file(root / p) if (root / p).is_file() else None}
                       for st, p in changes]
            return _build_dbt(cfg, work, canary_dir, "git", (m0, m1), (t0 / prel, t1 / prel),
                              {"mode": "git", "base_commit": commit, "target": prel, "changed": changed},
                              {"mode": "git", "repo": str(root), "base": cfg.base, "base_commit": commit,
                               "path": str(project.resolve()), "command": None}, notes,
                              [project, *(project / d for d in ("seeds", "data", "tests/fixtures")), root])
        if target_abs.is_file() and target_abs.suffix.lower() != ".sql":
            raise PlanError(f"{rel} is part of a dbt project; install dbt-core and dbt-duckdb to check changes to it")
    if rel is not None and not (t0 / rel).exists():
        raise PlanError(f"{rel} does not exist in {cfg.base}; there is no original to compare against")
    if rel is not None and target_abs.is_dir() and not is_model_folder(t0 / rel):
        raise PlanError(f"{rel} has no .sql models in {cfg.base}; there is no original to compare against")
    if rel is not None and (is_sql(cfg, t0 / rel, t1 / rel) or is_frame(cfg, Path(rel))):
        changed = [{"path": p, "status": st, "sha256": sha256_file(root / p) if (root / p).is_file() else None}
                   for st, p in changes]
        return _build_tables(
            cfg, work, canary_dir, "git", Side("original", t0, Path(rel)), Side("fix", t1, Path(rel)),
            {"mode": "git", "base_commit": commit, "target": rel, "changed": changed},
            {"mode": "git", "repo": str(root), "base": cfg.base, "base_commit": commit,
             "path": str(target_abs.resolve()), "command": None}, notes,
            (t0 / rel) if (t0 / rel).is_dir() else None,
            _roots_near(target_abs.resolve(), [root]))

    if cfg.sample:
        sample_path = cfg.resolve(cfg.sample)
    else:
        sample_path = discover_sample(target_abs.parent if target_abs else root, [root], target_abs)
        notes.append(f"sample: found {sample_path.relative_to(root) if sample_path.is_relative_to(root) else sample_path}")
    if not sample_path.is_file():
        raise PlanError(f"sample file not found: {sample_path}")
    sample = sample_path.read_bytes()
    fmt = sample_format(sample_path, sample)

    script = Path(rel) if rel else None
    side_b, side_a = Side("original", t0, script), Side("fix", t1, script)
    template = cfg.command or cfg.run
    inv = _base_invocation(cfg, sample_path, template, require_script=cfg.command is None)
    if not template:
        if rel is None:
            raise PlanError("pass --command to say how to run the code")
        prog = program_for(t1 / rel) or program_for(t0 / rel)
        if not prog:
            raise PlanError(f"cannot tell how to run {rel}; pass --run, e.g. --run 'python3 {{script}} {{input}}'")
        inv.template, _ = detect_run(work, side_b, prog, sample, inv)
        notes.append(f"run command: detected '{inv.template}'")
    output = _finish(cfg, inv, notes, fmt)
    inv.output_suffix = _output_suffix(output, fmt, cfg, inv.input_suffix)

    changed = []
    for status, p in changes:
        f = root / p
        changed.append({"path": p, "status": status,
                        "sha256": sha256_file(f) if f.is_file() else None})
    return _with_incident(Plan(
        mode="git", before=side_b, after=side_a, invocation=inv, sample_path=sample_path.resolve(),
        sample=sample, output=output, work=work, canary_dir=canary_dir, notes=notes, sample_format=fmt,
        inputs={"mode": "git", "base_commit": commit, "target": rel, "changed": changed,
                "sample": {"name": sample_path.name, "sha256": sha256_bytes(sample)}},
        replay={"mode": "git", "repo": str(root), "base": cfg.base, "base_commit": commit,
                "path": str(target_abs.resolve()) if target_abs else None, "command": cfg.command,
                "run": inv.template, "sample": str(sample_path.resolve())},
    ), *_load_incident(cfg), cfg)
