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
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from fixwitness.config import Config, ConfigError
from fixwitness.runner import Invocation, RunConfigError, Side, no_network_available, run_side

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


def discover_sample(near: Path, extra_roots: list[Path]) -> Path:
    found: list[Path] = []
    for root in [near, *extra_roots]:
        for sub in SAMPLE_DIRS:
            d = root / sub if sub else root
            if d.is_dir():
                found += sorted(p for p in d.glob("*.csv") if p.is_file())
    unique = list(dict.fromkeys(p.resolve() for p in found))
    if len(unique) == 1:
        return unique[0]
    if not unique:
        raise PlanError(f"no sample CSV found near {near}; pass one with --sample")
    listing = "\n".join(f"  {p}" for p in unique[:10])
    raise PlanError(f"several CSV files could be the sample; pick one with --sample:\n{listing}")


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


# ---------------------------------------------------------------- build

def build_plan(cfg: Config) -> Plan:
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


def _base_invocation(cfg: Config, sample_path: Path, template: str | None, require_script: bool) -> Invocation:
    output = cfg.output or "csv"
    return Invocation(template=template or "", timeout=cfg.timeout, allow_any=cfg.allow_any_command,
                      pass_env=cfg.pass_env, no_network=cfg.no_network,
                      input_suffix=sample_path.suffix or ".csv",
                      output_suffix=".csv" if output == "csv" else ".txt", require_script=require_script)


def _finish(cfg: Config, inv: Invocation, plan_notes: list[str]) -> str:
    """Pick the comparison mode once the run command is known."""
    if cfg.output:
        return cfg.output
    if "{output}" in inv.template and inv.input_suffix.lower() == ".csv":
        return "csv"
    if inv.input_suffix.lower() == ".csv":
        plan_notes.append("output is standard output; it is compared as CSV if it parses, else as text")
        return "csv"
    return "text"


def _build_files(cfg: Config, work: Path, canary_dir: Path) -> Plan:
    before, after = cfg.resolve(cfg.before), cfg.resolve(cfg.after)
    for label, p in (("before", before), ("after", after)):
        if not p.is_file():
            raise PlanError(f"{label} file not found: {p}")
    notes: list[str] = []
    if cfg.sample:
        sample_path = cfg.resolve(cfg.sample)
    else:
        sample_path = discover_sample(after.parent, [before.parent])
        notes.append(f"sample: found {sample_path.name} next to the script")
    if not sample_path.is_file():
        raise PlanError(f"sample file not found: {sample_path}")
    sample = sample_path.read_bytes()
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
    output = _finish(cfg, inv, notes)
    inv.output_suffix = ".csv" if output == "csv" else ".txt"
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
    return plan


def _build_git(cfg: Config, work: Path, canary_dir: Path) -> Plan:
    target_abs = cfg.resolve(cfg.path) if cfg.path else None
    if target_abs is not None and not target_abs.is_file():
        raise PlanError(f"file not found: {target_abs}")
    anchor = target_abs.parent if target_abs is not None else cfg.base_dir
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
        if rel not in {p for _, p in changes}:
            notes.append(f"{rel} itself is unchanged; comparing because other files changed")

    t0, t1 = work / "trees" / "t0", work / "trees" / "t1"
    export_commit(root, commit, t0)
    snapshot_worktree(root, t1)
    if rel is not None and not (t0 / rel).is_file():
        raise PlanError(f"{rel} does not exist in {cfg.base}; there is no original to compare against")

    if cfg.sample:
        sample_path = cfg.resolve(cfg.sample)
    else:
        sample_path = discover_sample(target_abs.parent if target_abs else root, [root])
        notes.append(f"sample: found {sample_path.relative_to(root) if sample_path.is_relative_to(root) else sample_path}")
    if not sample_path.is_file():
        raise PlanError(f"sample file not found: {sample_path}")
    sample = sample_path.read_bytes()

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
    output = _finish(cfg, inv, notes)
    inv.output_suffix = ".csv" if output == "csv" else ".txt"

    changed = []
    for status, p in changes:
        f = root / p
        changed.append({"path": p, "status": status,
                        "sha256": sha256_file(f) if f.is_file() else None})
    return _with_incident(Plan(
        mode="git", before=side_b, after=side_a, invocation=inv, sample_path=sample_path.resolve(),
        sample=sample, output=output, work=work, canary_dir=canary_dir, notes=notes,
        inputs={"mode": "git", "base_commit": commit, "target": rel, "changed": changed,
                "sample": {"name": sample_path.name, "sha256": sha256_bytes(sample)}},
        replay={"mode": "git", "repo": str(root), "base": cfg.base, "base_commit": commit,
                "path": str(target_abs.resolve()) if target_abs else None, "command": cfg.command,
                "run": inv.template, "sample": str(sample_path.resolve())},
    ), *_load_incident(cfg), cfg)
