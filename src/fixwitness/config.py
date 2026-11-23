"""Settings, from a fixwitness.toml file and/or command-line / MCP arguments."""

from __future__ import annotations

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
    tolerance: float = 0.0
    unordered: bool = False
    auto_ignore_unstable: bool = True
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
        if self.before or self.after:
            if not (self.before and self.after):
                raise ConfigError("give both --before and --after, or use a changed file in git instead")
            return "files"
        if self.path or self.command:
            return "git"
        raise ConfigError(
            "tell fixwitness what to check, for example:\n"
            "  fixwitness check etl/clean.py --sample data/sample.csv      (your change vs git HEAD)\n"
            "  fixwitness check --before old.py --after new.py --sample s.csv\n"
            "  fixwitness check --base main --command 'python3 etl/run.py {input} {output}' --sample s.csv"
        )

    def validate(self) -> None:
        self.mode()
        if self.output not in (None, "csv", "text"):
            raise ConfigError("output must be 'csv' or 'text'")
        if not 10 <= self.max_cases <= 5000:
            raise ConfigError("max_cases must be between 10 and 5000")
        if self.tolerance < 0:
            raise ConfigError("tolerance must be 0 or positive")
        if self.timeout <= 0:
            raise ConfigError("timeout must be positive")


_KEYS = {f for f in Config.__dataclass_fields__ if f != "base_dir"}
_PATH_KEYS = {"path", "before", "after", "sample", "incident", "incident_expected"}
_ALIASES = {"timeout_seconds": "timeout"}


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
        for section in ("fix", "cases", "compare", "runtime"):
            data.update(raw.get(section, {}))
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
    for name in ("columns", "review", "ignore_columns", "ignore_patterns", "pass_env"):
        value = getattr(cfg, name)
        if isinstance(value, str):
            setattr(cfg, name, [v.strip() for v in value.split(",") if v.strip()])
    cfg.max_cases, cfg.rows, cfg.seed, cfg.workers = int(cfg.max_cases), int(cfg.rows), int(cfg.seed), int(cfg.workers)
    cfg.timeout, cfg.tolerance = float(cfg.timeout), float(cfg.tolerance)
    cfg.validate()
    return cfg
