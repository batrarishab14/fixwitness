"""Run one side (original or fix) on one case.

Both sides of a case run one after the other in the *same* case directory, so absolute
input and output paths are identical and cannot cause false differences.

This is process isolation, not a security sandbox: scripts run as the current user. Use
``--no-network`` (Linux user namespaces) and a container for untrusted code.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from fixwitness.cases import TEMPLATE_MARKER

ALLOWED_PROGRAMS = {
    "python", "python3", "bash", "sh", "zsh", "dash", "node", "deno", "ruby", "perl",
    "php", "Rscript", "pwsh", "java", "duckdb", "sqlite3", "uv", "poetry",
}
_PYTHON_VERSIONED = re.compile(r"python3(\.\d+)?")
NO_NETWORK_PREFIX = ["unshare", "--user", "--map-root-user", "--net", "--"]


class RunConfigError(ValueError):
    pass


@dataclass
class Command:
    argv: list[str]
    stdin_from_input: bool
    output_from: str  # "file" or "stdout"


@dataclass
class Side:
    label: str               # "original" or "fix"
    root: Path | None        # working directory (git mode); None = the case directory
    script: Path | None      # value substituted for {script}


@dataclass
class Invocation:
    template: str
    timeout: float = 10.0
    allow_any: bool = False
    pass_env: list[str] = field(default_factory=list)
    no_network: bool = False
    input_suffix: str = ".csv"
    output_suffix: str = ".csv"
    require_script: bool = True


@dataclass
class RunResult:
    exit_code: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    output: bytes | None
    exploited: bool
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and not self.timed_out and self.exit_code == 0


def build_command(template: str, script: str | None, input_path: str, output_path: str,
                  allow_any: bool, require_script: bool = True) -> Command:
    """Turn the run template into argv. No shell is involved, so values and paths can't inject."""
    try:
        tokens = shlex.split(template)
    except ValueError as exc:
        raise RunConfigError(f"cannot parse run command {template!r}: {exc}") from exc
    if not tokens:
        raise RunConfigError("run command is empty")
    if require_script and "{script}" not in template:
        raise RunConfigError("run command must contain {script}")
    if "{input}" not in template:
        raise RunConfigError("run command must contain {input} (as an argument or as '< {input}')")

    stdin_from_input = False
    output_from = "file" if "{output}" in template else "stdout"
    cleaned: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "<" and i + 1 < len(tokens) and tokens[i + 1] == "{input}":
            stdin_from_input = True
            i += 2
            continue
        if tok == ">" and i + 1 < len(tokens) and tokens[i + 1] == "{output}":
            output_from = "stdout"
            i += 2
            continue
        if tok in ("<", ">", "|", "&&", ";", "||"):
            raise RunConfigError(f"shell operator {tok!r} is not supported in the run command (no shell is used)")
        cleaned.append(tok)
        i += 1

    def sub(t: str) -> str:
        return t.replace("{script}", script or "").replace("{input}", input_path).replace("{output}", output_path)

    argv = [sub(t) for t in cleaned]
    program = os.path.basename(argv[0])
    if not allow_any and program not in ALLOWED_PROGRAMS and not _PYTHON_VERSIONED.fullmatch(program):
        raise RunConfigError(
            f"program {program!r} is not in the allowed list ({', '.join(sorted(ALLOWED_PROGRAMS))}); "
            "run it through an interpreter (e.g. 'bash run.sh ...') or pass --allow-any-command"
        )
    return Command(argv, stdin_from_input, output_from)


def no_network_available() -> bool:
    if not shutil.which("unshare"):
        return False
    try:
        return subprocess.run(NO_NETWORK_PREFIX[:-1] + ["true"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _kill_group(proc: subprocess.Popen) -> None:
    if hasattr(os, "killpg"):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    else:  # Windows
        try:
            proc.kill()
        except OSError:
            pass


def run_side(inv: Invocation, side: Side, case_dir: Path, content: bytes,
             canary: str | None = None, oracle: str | None = None,
             canary_dir: Path | None = None) -> RunResult:
    work = case_dir / "w"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    input_path = work / f"input{inv.input_suffix}"
    output_path = work / f"output{inv.output_suffix}"
    input_path.write_bytes(content)

    cwd = side.root if side.root is not None else work
    if side.root is None:  # file mode: relative names, identical for both sides
        in_arg, out_arg = input_path.name, output_path.name
    else:
        in_arg, out_arg = str(input_path), str(output_path)
    cmd = build_command(inv.template, str(side.script) if side.script else None, in_arg, out_arg,
                        inv.allow_any, inv.require_script)
    argv = (NO_NETWORK_PREFIX + cmd.argv) if inv.no_network else cmd.argv

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(work),
        "TMPDIR": str(work),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    }
    for name in inv.pass_env:
        if name in os.environ:
            env[name] = os.environ[name]

    stdin = open(input_path, "rb") if cmd.stdin_from_input else subprocess.DEVNULL
    timed_out = False
    try:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=stdin, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, start_new_session=True)
        except OSError as exc:
            return RunResult(None, False, b"", b"", None, False, error=f"could not start {argv[0]!r}: {exc}")
        try:
            out, err = proc.communicate(timeout=inv.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
            out, err = proc.communicate()
        _kill_group(proc)  # stop anything the script left running in the background
    finally:
        if stdin is not subprocess.DEVNULL:
            stdin.close()

    if cmd.output_from == "file":
        output = output_path.read_bytes() if output_path.exists() else None
    else:
        output = out
    exploited = _exploited(canary, oracle, canary_dir, output, out, content)
    return RunResult(None if timed_out else proc.returncode, timed_out, out, err, output, exploited)


def _exploited(canary, oracle, canary_dir: Path | None, output: bytes | None, stdout: bytes,
               content: bytes) -> bool:
    if oracle == "output":
        marker = TEMPLATE_MARKER.encode()
        if marker in content:
            return False  # the input already contains the marker; the oracle can't decide
        return marker in (output or b"") or marker in stdout
    if oracle != "file" or not canary or canary_dir is None:
        return False
    hits = list(canary_dir.glob(canary + "*"))
    for hit in hits:
        try:
            hit.unlink() if hit.is_file() or hit.is_symlink() else shutil.rmtree(hit)
        except OSError:
            pass
    return bool(hits)
