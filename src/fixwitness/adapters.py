"""Plug-in adapters: teach `fixwitness check` (with no file named) a new kind of code.

An adapter is any object with:

    name: str                                  shown in the report as "Checked as"
    claims(path: Path, root: Path) -> bool     does this adapter check this changed file?
    settings(path: Path, root: Path) -> dict   the fixwitness settings for its check: the same keys
                                               as fixwitness.toml, e.g.
                                               {"run": "go run {script} {input} {output}",
                                                "sample": "testdata/orders.csv"}

Adapters are asked first, in the order they are found, so an adapter can also take over a file
fixwitness would otherwise check its own way.

Register one in a package (pyproject.toml):

    [project.entry-points."fixwitness.adapters"]
    go = "fixwitness_go:GoAdapter"

or, inside one repository, without packaging it:

    FIXWITNESS_ADAPTERS="tools/fw_adapters.py:GoAdapter"    (several: separated by commas)

See docs/ADAPTERS.md for a complete example.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

ENV = "FIXWITNESS_ADAPTERS"
GROUP = "fixwitness.adapters"


def _load_ref(ref: str, root: Path):
    target, _, attr = ref.strip().rpartition(":")
    if not target or not attr:
        raise ValueError(f"{ref!r}: write MODULE:ATTRIBUTE or FILE.py:ATTRIBUTE")
    if target.endswith(".py"):
        path = Path(target) if Path(target).is_absolute() else root / target
        spec = importlib.util.spec_from_file_location(f"fixwitness_adapter_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(target)
    obj = getattr(module, attr)
    return obj() if isinstance(obj, type) else obj


def load_adapters(root: Path) -> list:
    """Every adapter that loads; one that fails to load is reported and left out."""
    found = []
    try:
        from importlib.metadata import entry_points
        for ep in entry_points(group=GROUP):
            try:
                obj = ep.load()
                found.append(obj() if isinstance(obj, type) else obj)
            except Exception as exc:
                print(f"fixwitness: adapter {ep.name} did not load: {exc}", file=sys.stderr)
    except Exception:
        pass
    for ref in filter(None, (os.environ.get(ENV) or "").split(",")):
        try:
            found.append(_load_ref(ref, root))
        except Exception as exc:
            print(f"fixwitness: adapter {ref} did not load: {exc}", file=sys.stderr)
    usable = []
    for a in found:
        if all(hasattr(a, k) for k in ("name", "claims", "settings")):
            usable.append(a)
        else:
            print(f"fixwitness: {a!r} is not an adapter (it needs name, claims and settings)", file=sys.stderr)
    return usable


def claim(adapters: list, path: Path, root: Path) -> tuple[str, dict] | None:
    """(kind, settings) from the first adapter that claims the file."""
    for a in adapters:
        try:
            if a.claims(path, root):
                return str(a.name), dict(a.settings(path, root) or {})
        except Exception as exc:
            print(f"fixwitness: adapter {getattr(a, 'name', a)!r} failed on {path}: {exc}", file=sys.stderr)
    return None
