# Adapters: checking a new kind of code

`fixwitness check` with no file named classifies every changed file: dbt projects, SQL files, DataFrame functions and scripts. An adapter teaches it another kind, for example Go jobs, Airflow tasks or a team's own ETL runner, without changing fixwitness.

An adapter is any Python object with three members:

| Member | What it does |
|---|---|
| `name` | Shown in the report as "Checked as" |
| `claims(path, root)` | True when the adapter checks this changed file (`path`, inside the repository `root`) |
| `settings(path, root)` | The settings for its check, with the same keys as `fixwitness.toml` |

Adapters are asked before the built-in kinds, in the order they are found.

## Example: Go jobs that read a CSV and write a CSV

```python
# tools/fw_adapters.py
from pathlib import Path


class GoJob:
    name = "go job"

    def claims(self, path: Path, root: Path) -> bool:
        return path.suffix == ".go" and (path.parent / "testdata" / "sample.csv").is_file()

    def settings(self, path: Path, root: Path) -> dict:
        return {"run": "go run {script} {input} {output}",
                "sample": str(path.parent / "testdata" / "sample.csv"),
                "attacks": False}
```

Use it in one repository:

```bash
FIXWITNESS_ADAPTERS=tools/fw_adapters.py:GoJob fixwitness check --allow-any-command
```

`go` is not on fixwitness's list of programs it runs without asking, so this needs `--allow-any-command` (or `allow_any_command = true` in `fixwitness.toml`).

Or publish it as a package, so every repository that installs it gets the adapter:

```toml
# pyproject.toml of your adapter package
[project.entry-points."fixwitness.adapters"]
go = "fixwitness_go:GoJob"
```

## Rules

- `settings` may return any key of `fixwitness.toml`. Relative paths in `sample`, `incident`, `incident_expected`, `before` and `after` are read from the repository root.
- A setting fixwitness doesn't have is reported as "not checked" for that file, with the reason; the other files are still checked.
- An adapter that fails to load, or raises, is reported on standard error and left out.
- The run command must start with a program on the allow-list (`python3`, `node`, `ruby`, `Rscript`, `java`, `bash`, ...) unless the user passes `--allow-any-command`. An adapter can't lift that limit by itself.
