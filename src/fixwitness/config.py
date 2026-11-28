"""Settings, from a fixwitness.toml file and/or command-line / MCP arguments."""

from __future__ import annotations

import re

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    # What to compare: a changed file in git (path), an entry command in git, or two files.
    path: str | None = None
    base: str = "HEAD"
    command: str | None = None
    before: str | None = None
    after: str | None = None
    sample: str | None = None
    run: str | None = None
    run_after: str | None = None          # a different run command for the fix (e.g. a shell script rewritten in Python)
    # Self-healing / repair: an input that broke the original. The fix must handle it.
    incident: str | None = None
    incident_expected: str | None = None    # optional: the correct output for the incident input
    # SQL and dbt models: table name -> sample CSV (and incident CSVs), engine, row order
    tables: dict[str, str] | None = None
    incident_tables: dict[str, str] | None = None
    engine: str = "auto"                    # auto (DuckDB if installed, else SQLite), duckdb, sqlite
    dbt: str = "auto"                       # render ref()/source()/config(): auto (when {{ appears), on, off
    sql_ordered: bool = False               # compare result rows in order (default: as a set of rows)
    dialect: str | None = None              # the SQL is written for this warehouse (snowflake, bigquery, ...);
                                            # translated with sqlglot to the engine's dialect
    sql_outputs: list[str] | None = None    # a folder of models: the models to compare (default: the final
                                            # ones, which no other model reads); ["all"] for every model
    # dbt projects: manifests your CI already compiled (otherwise fixwitness compiles with dbt-duckdb)
    manifest: str | None = None             # the fix's target/manifest.json
    base_manifest: str | None = None        # the original's
    # Python DataFrame code: the function to call with the tables (pandas, polars or PySpark)
    function: str | None = None
    library: str = "auto"                   # auto (from the script's imports), pandas, polars, pyspark
    # Cases
    attacks: bool = True                    # run attack payloads (turn off for pure repairs/refactors)
    columns: list[str] | None = None
    review: list[str] = field(default_factory=list)
    max_cases: int = 300
    rows: int = 3
    seed: int = 1337
    # Comparison
    output: str | None = None
    ignore_columns: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)
    # A bug fix that should change some output columns (model.column or column): the check passes
    # when those are the only columns that change, and says on which inputs they changed.
    expect_change: list[str] = field(default_factory=list)
    tolerance: float = 0.0
    unordered: bool = False
    auto_ignore_unstable: bool = True
    shrink: bool = True                     # shrink each difference to the smallest input that shows it
    # A PASS on code no input reached proves nothing: report "not exercisable with this data" instead
    # (INCONCLUSIVE) when the change tests a value no input has, or uses a column that is empty everywhere
    exercise_check: bool = True
    # A data change (attacks off) that crashes on a malformed-text input the original ran (a number written 2_500,
    # padded with spaces ...) is reported as a robustness finding, not a failure; a changed VALUE always fails.
    strict_robustness: bool = False
    # Library migrations (pandas -> Polars ...) print the same number differently ("1" / "1.0", "1e+30" / "1e30"):
    # compare numbers by value (exact decimal equality; a lost digit still differs, "007" stays text).
    same_numbers: bool = False
    # Differences someone marked as intended ([[accept]] in fixwitness.toml): inputs of that category
    # (and column) for that target are reported as "reviewed", not failed.
    accept: list[dict] | None = None
    # SQL/dbt: run both versions in your warehouse instead of DuckDB/SQLite (postgres://, snowflake://,
    # bigquery://); no password in the URL
    warehouse: str | None = None
    # Runtime
    timeout: float = 10.0
    workers: int = 0
    pass_env: list[str] = field(default_factory=list)
    allow_any_command: bool = False
    no_network: bool = False
    # Where relative paths resolve (the config file's folder, or the current folder)
    base_dir: Path = field(default_factory=Path.cwd)

    def resolve(self, value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else (self.base_dir / p)

    def mode(self) -> str:
        if self.manifest or self.base_manifest:
            if not (self.manifest and self.base_manifest):
                raise ConfigError("give both --manifest (the fix's) and --base-manifest (the original's)")
            if not (self.before or self.after or self.path):
                return "files"
        if self.before or self.after:
            if not (self.before and self.after):
                raise ConfigError("give both --before and --after, or use a changed file in git instead")
            return "files"
        return "git"  # with no file named: every change in the working tree (see changes.py)

    def require_target(self) -> None:
        if self.mode() == "git" and not (self.path or self.command):
            raise ConfigError(NO_TARGET)

    def validate(self) -> None:
        self.mode()
        if self.output not in (None, "csv", "json", "text"):
            raise ConfigError("output must be 'csv', 'json' or 'text'")
        if not 10 <= self.max_cases <= 5000:
            raise ConfigError("max_cases must be between 10 and 5000")
        if self.tolerance < 0:
            raise ConfigError("tolerance must be 0 or positive")
        if self.timeout <= 0:
            raise ConfigError("timeout must be positive")
        if self.warehouse is not None:
            from fixwitness.warehouse import WarehouseError, parse_url
            try:
                parse_url(self.warehouse)
            except WarehouseError as exc:
                raise ConfigError(str(exc)) from None
        if self.engine not in ("auto", "duckdb", "sqlite"):
            raise ConfigError("engine must be auto, duckdb or sqlite")
        if self.dbt not in ("auto", "on", "off"):
            raise ConfigError("dbt must be auto, on or off")
        if self.dialect is not None and (not isinstance(self.dialect, str) or not _DIALECT.fullmatch(self.dialect)):
            raise ConfigError("dialect must be a SQL dialect name such as snowflake, bigquery, postgres or tsql")
        if self.function is not None and not (isinstance(self.function, str) and _IDENT.fullmatch(self.function)):
            raise ConfigError("function must be the name of a Python function")
        if self.library not in ("auto", "pandas", "polars", "pyspark"):
            raise ConfigError("library must be auto, pandas, polars or pyspark")
        if self.sql_outputs is not None and (not isinstance(self.sql_outputs, list) or not all(
                isinstance(o, str) and o for o in self.sql_outputs)):
            raise ConfigError("sql_outputs must be a list of model names")
        for name in ("tables", "incident_tables"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, dict) or not all(
                    isinstance(k, str) and isinstance(v, str) for k, v in value.items())):
                raise ConfigError(f"{name} must map table names to CSV file paths")
        if self.accept is not None and (not isinstance(self.accept, list) or not all(
                isinstance(a, dict) and isinstance(a.get("category"), str) and set(a) <= _ACCEPT_KEYS
                for a in self.accept)):
            raise ConfigError("each [[accept]] needs a category, and may have target, column and note")
        if self.incident_tables and not self.tables and not self.sample:
            raise ConfigError("incident_tables needs tables (the sample tables)")


NO_TARGET = (
    "tell fixwitness what to check, for example:\n"
    "  fixwitness check                                            (every change in your working tree)\n"
    "  fixwitness check etl/clean.py --sample data/sample.csv      (your change vs git HEAD)\n"
    "  fixwitness check --before old.py --after new.py --sample s.csv\n"
    "  fixwitness check --base main --command 'python3 etl/run.py {input} {output}' --sample s.csv"
)

_KEYS = {f for f in Config.__dataclass_fields__ if f != "base_dir"}
_DIALECT = re.compile(r"[a-z][a-z0-9_]*")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PATH_KEYS = {"path", "before", "after", "sample", "incident", "incident_expected", "manifest", "base_manifest"}
_ALIASES = {"timeout_seconds": "timeout"}
_ACCEPT_KEYS = {"target", "category", "column", "note"}


def load_config(path: Path | None, overrides: dict) -> Config:
    data: dict = {}
    base_dir = Path.cwd()
    if path is not None:
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        try:
            with path.open("rb") as fh:
                raw = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"{path}: {exc}") from exc
        base_dir = path.resolve().parent
        for section in ("fix", "cases", "compare", "runtime", "sql"):
            data.update(raw.get(section, {}))
        if "accept" in raw:
            data["accept"] = raw["accept"]
    for k, v in overrides.items():
        if v is None:
            continue
        if k in _PATH_KEYS and isinstance(v, str) and not Path(v).expanduser().is_absolute():
            v = str(Path.cwd() / Path(v).expanduser())  # command-line paths are relative to where you are
        data[k] = v
    for alias, real in _ALIASES.items():
        if alias in data:
            data[real] = data.pop(alias)
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        raise ConfigError(f"unknown setting(s): {', '.join(unknown)}")
    cfg = Config(base_dir=base_dir, **data)
    for name in ("columns", "review", "ignore_columns", "ignore_patterns", "expect_change", "pass_env"):
        value = getattr(cfg, name)
        if isinstance(value, str):
            setattr(cfg, name, [v.strip() for v in value.split(",") if v.strip()])
    cfg.max_cases, cfg.rows, cfg.seed, cfg.workers = int(cfg.max_cases), int(cfg.rows), int(cfg.seed), int(cfg.workers)
    cfg.timeout, cfg.tolerance = float(cfg.timeout), float(cfg.tolerance)
    cfg.validate()
    return cfg


def append_accept(path: Path, target: str | None, category: str, column: str | None, note: str | None) -> dict:
    """Record a difference as intended: add an [[accept]] table to fixwitness.toml (created if missing)."""
    import json
    entry = {k: v for k, v in (("target", target), ("category", category), ("column", column),
                               ("note", note)) if v}
    if path.is_file():
        with path.open("rb") as fh:
            existing = tomllib.load(fh).get("accept", [])
        if entry in existing:
            return entry
        text = path.read_text(encoding="utf-8")
    else:
        text = "# fixwitness settings\n"
    lines = ["", "[[accept]]  # a difference marked as intended: reported as reviewed, not failed"]
    lines += [f"{k} = {json.dumps(v)}" for k, v in entry.items()]
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return entry
