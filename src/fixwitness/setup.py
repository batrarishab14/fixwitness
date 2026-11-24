"""fixwitness setup: connect fixwitness to the tools you already use, in one command.

    fixwitness setup claude      .mcp.json            (Claude Code)
    fixwitness setup cursor      .cursor/mcp.json     (Cursor)
    fixwitness setup vscode      .vscode/mcp.json     (VS Code agent mode, GitHub Copilot)
    fixwitness setup github      .github/workflows/fixwitness.yml (a check and a comment on every pull request)
    fixwitness setup pre-commit  .pre-commit-config.yaml (a check before each commit)

Existing files are merged, never overwritten: a server or hook already there is left as it is.
With --instructions, a short note is added to CLAUDE.md or AGENTS.md telling coding agents to call
prove_change before they finish a change to data code.
"""

from __future__ import annotations

import json
from pathlib import Path

SERVER = {"command": "fixwitness", "args": ["mcp"]}

WORKFLOW = """\
# Checks every change a pull request makes to data code (dbt, SQL, pandas/polars, scripts)
# and comments with the result. https://github.com/batrarishab14/fixwitness
name: fixwitness
on: pull_request
permissions:
  contents: read
  pull-requests: write
jobs:
  fixwitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: batrarishab14/fixwitness@v0.6.0
        with:
          install: {install}
          args: --no-attacks
"""

PRE_COMMIT = """\
  - repo: https://github.com/batrarishab14/fixwitness
    rev: v0.6.0
    hooks:
      - id: fixwitness
"""

INSTRUCTIONS = """
## Checking changes to data code (fixwitness)

Before you finish a change to SQL, dbt models, DataFrame code or a data job, call the `prove_change`
tool of the fixwitness MCP server (or run `fixwitness check --no-attacks`). If the verdict is FAIL,
read each finding, fix the change or explain why the difference is intended, and check again.
Put the verdict and the proof IDs in the pull request description.
"""


def _merge_json(path: Path, key: str, name: str, entry: dict) -> str:
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            return f"{path}: not valid JSON, left unchanged; add {json.dumps({key: {name: entry}})} yourself"
    servers = data.setdefault(key, {})
    if name in servers:
        return f"{path}: already has a '{name}' server, left unchanged"
    servers[name] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"{path}: added the fixwitness MCP server"


def _libraries(root: Path) -> str:
    """The optional libraries the repository's code seems to use, for the Action's install input."""
    want = ["duckdb"]
    if any(root.rglob("dbt_project.yml")):
        want.append("dbt")
    text = ""
    for p in list(root.rglob("*.py"))[:400]:
        if ".git" in p.parts or "site-packages" in p.parts:
            continue
        try:
            text += p.read_text(encoding="utf-8", errors="ignore")[:20000]
        except OSError:
            pass
    for lib in ("pandas", "polars", "pyarrow"):
        if f"import {lib}" in text or f"from {lib}" in text:
            want.append(lib)
    return ",".join(want)


def setup(target: str, root: Path, instructions: bool = False) -> list[str]:
    done = []
    if target == "claude":
        done.append(_merge_json(root / ".mcp.json", "mcpServers", "fixwitness", SERVER))
        note_file = root / "CLAUDE.md"
    elif target == "cursor":
        done.append(_merge_json(root / ".cursor" / "mcp.json", "mcpServers", "fixwitness", SERVER))
        note_file = root / "AGENTS.md"
    elif target == "vscode":
        done.append(_merge_json(root / ".vscode" / "mcp.json", "servers", "fixwitness", {"type": "stdio", **SERVER}))
        note_file = root / "AGENTS.md"
    elif target == "github":
        path = root / ".github" / "workflows" / "fixwitness.yml"
        if path.exists():
            done.append(f"{path}: already exists, left unchanged")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(WORKFLOW.format(install=_libraries(root)), encoding="utf-8")
            done.append(f"{path}: added (checks every pull request and comments with the result)")
        note_file = None
    elif target == "pre-commit":
        path = root / ".pre-commit-config.yaml"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if "batrarishab14/fixwitness" in text:
            done.append(f"{path}: already has the fixwitness hook, left unchanged")
        elif text and "repos:" not in text:
            done.append(f"{path}: no 'repos:' list found; add this under it yourself:\n{PRE_COMMIT}")
        else:
            text = (text.rstrip("\n") + "\n" if text else "repos:\n") + PRE_COMMIT
            path.write_text(text, encoding="utf-8")
            done.append(f"{path}: added the fixwitness hook (run `pre-commit install` once)")
        note_file = None
    else:
        raise ValueError(f"unknown target {target!r}: use claude, cursor, vscode, github or pre-commit")
    if instructions and note_file is not None:
        text = note_file.read_text(encoding="utf-8") if note_file.is_file() else ""
        if "prove_change" in text:
            done.append(f"{note_file}: already tells agents to call prove_change")
        else:
            note_file.write_text(text.rstrip("\n") + "\n" + INSTRUCTIONS if text else INSTRUCTIONS.lstrip("\n"),
                                 encoding="utf-8")
            done.append(f"{note_file}: added a note telling coding agents to call prove_change")
    return done
