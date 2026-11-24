"""Run a check and build the proof record."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import shutil
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fixwitness import __version__
from fixwitness.cases import CATEGORY_DESCRIPTIONS, Case, SampleError, column_types, generate_cases
from fixwitness.formats import (JSON_CATEGORY_DESCRIPTIONS, generate_json_cases, generate_parquet_cases,
                                json_paths, parse_json_sample, parquet_to_csv, unstable_json_paths)
from fixwitness.sql import generate_sql_cases, link_tables
from fixwitness.compare import CompareOptions, compare, output_headers, parse_rows, unstable_columns
from fixwitness.config import Config, ConfigError
from fixwitness.plan import Plan, PlanError, build_plan, sha256_file
from fixwitness.runner import RunResult, run_side
from fixwitness.score import confidence

LIMITATIONS = [
    "Evidence covers only the input categories fixwitness generated; inputs outside them were not tested.",
    "This is differential testing, not a formal proof of equivalence.",
    "Attack checks use built-in payloads (command/code injection, path traversal, template injection); "
    "other vulnerability classes are not tested.",
    "Scripts ran on this machine in temporary directories (process isolation, not a sandbox).",
]


# Inputs and outputs of the differences, kept per proof (not in proof.json: bytes, and not evidence
# of their own) so that write_outputs can save a runnable reproduction of each one.
REPRO: dict[str, dict] = {}
MAX_REPROS = 25


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _short(value: str | None, limit: int = 80) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[: limit - 3] + "..."


def _tail(data: bytes, limit: int = 300) -> str:
    return data.decode("utf-8", errors="replace").strip()[-limit:]


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error as exc:
            raise ConfigError(f"bad --ignore-pattern {p!r}: {exc}") from exc
    return compiled


def _evaluate(case: Case, before: RunResult, after: RunResult, opts: CompareOptions,
              expected: CompareOptions | None = None) -> tuple[dict, list[str]]:
    entry = {
        "id": case.id, "category": case.category, "kind": case.kind, "column": case.column,
        "family": case.family, "value": _short(case.value),
        "before": {"exit": before.exit_code, "timed_out": before.timed_out, "exploited": before.exploited},
        "after": {"exit": after.exit_code, "timed_out": after.timed_out, "exploited": after.exploited},
    }
    details: list[str] = []
    if case.kind == "attack":
        status = "still-exploitable" if after.exploited else ("blocked" if before.exploited else "not-triggered")
    elif not before.ok or before.output is None:
        status = "not-comparable"
        details.append("the original failed on this input: "
                       + (before.error or ("timed out" if before.timed_out else _tail(before.stderr)) or "no output"))
    elif not after.ok or after.output is None:
        status = "after-failed"
        details.append("the fix failed where the original worked: "
                       + (after.error or ("timed out" if after.timed_out else _tail(after.stderr)) or "no output"))
    else:
        status, details = compare(before.output, after.output, opts)
        if status == "changed" and expected is not None \
                and compare(before.output, after.output, expected)[0] in ("identical", "same-data"):
            status = "expected-change"  # only the columns the fix is meant to change differ
    entry["status"] = status
    return entry, details


def _baseline(plan: Plan, opts: CompareOptions, detect: bool) -> tuple[set[str], list[str], bytes | None]:
    """Run the original on the sample (twice when detecting non-deterministic columns)."""
    d = plan.work / "stability"
    first = run_side(plan.invocation, plan.before, d, plan.sample)
    second = run_side(plan.invocation, plan.before, d, plan.sample) if detect else first
    shutil.rmtree(d, ignore_errors=True)
    warnings: list[str] = []
    if not first.ok or first.output is None:
        warnings.append("the original failed on the sample itself: "
                        + (first.error or ("timed out" if first.timed_out else _tail(first.stderr)) or "no output"))
        return set(), warnings, None
    if first.output == second.output:
        return set(), warnings, first.output
    found = unstable_json_paths(first.output, second.output) if opts.mode == "json" else None
    if found is not None:
        cols, problem = found
        if problem:
            warnings.append(f"{problem}; use --unordered or --ignore-pattern")
        return cols, warnings, first.output
    if opts.mode == "csv" and parse_rows(first.output) is not None:
        cols, problem = unstable_columns(first.output, second.output)
        if problem:
            warnings.append(f"the original's output is not deterministic ({problem}); "
                            "use --unordered or --ignore-pattern")
        return cols, warnings, first.output
    warnings.append("the original's output changes between two runs on the same input; "
                    "mask the changing parts with --ignore-pattern")
    return set(), warnings, first.output


def _data_rows(data: bytes | None) -> int | None:
    rows = parse_rows(data) if data is not None else None
    return None if rows is None else max(0, len(rows) - 1)


def _check_incident(plan: Plan, opts: CompareOptions, baseline: bytes | None,
                    preserves_rows: bool) -> tuple[dict | None, dict | None]:
    """Run both sides on the input that broke the original.

    The fix must process it, and in a way consistent with how the original behaves on normal
    data: the same output columns, one output row per input row when the original always does
    that, and the expected output when one is given.
    """
    if plan.incident is None:
        return None, None
    d = plan.work / "incident"
    b = run_side(plan.invocation, plan.before, d, plan.incident)
    a = run_side(plan.fix_invocation, plan.after, d, plan.incident)
    shutil.rmtree(d, ignore_errors=True)
    b_ok, a_ok = b.ok and b.output is not None, a.ok and a.output is not None
    wrong = None  # the original ran, but its output is not the expected one: that is the incident too
    if b_ok and plan.incident_expected is not None:
        st, det = compare(plan.incident_expected, b.output, opts)
        if st == "changed":
            wrong = "wrong output: " + "; ".join(det[:2])
    status = "still-failing" if not a_ok else ("resolved" if (not b_ok or wrong) else "not-reproduced")

    problems: list[str] = []
    if a_ok and plan.output == "csv":
        fix_h, base_h = output_headers(a.output), output_headers(baseline) if baseline else None
        if fix_h is not None and base_h is not None and fix_h != base_h:
            show = (lambda h: h.get("", h)) if set(fix_h) == {""} else (lambda h: h)
            problems.append(f"its output columns {show(fix_h)} differ from the original's {show(base_h)}")
        fix_rows = parse_rows(a.output)
        n_in, n_out = _data_rows(plan.incident), (len(fix_rows) - 1 if fix_rows else None)
        if preserves_rows and n_in is not None and n_out is not None and n_in != n_out:
            problems.append(f"it wrote {n_out} rows for {n_in} input rows, while the original always writes "
                            "one row per input row (rows were dropped or added)")
    if a_ok and plan.incident_expected is not None:
        st, det = compare(plan.incident_expected, a.output, opts)
        if st == "changed":
            problems.append("its output differs from the expected output (" + "; ".join(det[:3]) + ")")
    if problems and status != "still-failing":
        status = "resolved-incorrectly"

    def why(r: RunResult) -> str:
        return r.error or ("timed out" if r.timed_out else _tail(r.stderr, 200)) or "no output"

    details = {"original": wrong if b_ok else why(b), "fix": None if a_ok else why(a), "problems": problems}
    checks = ["processes it"] + (["same columns"] if baseline and plan.output == "csv" else []) \
        + (["one row per input row"] if preserves_rows else []) \
        + (["expected output"] if plan.incident_expected is not None else [])
    return {"file": plan.incident_path.name, "status": status, "checks": checks}, details


def _sample_types(plan: Plan) -> dict:
    if plan.sample_format == "json":
        return json_paths(parse_json_sample(plan.sample)[1])
    if plan.sample_format == "parquet":
        return parquet_to_csv(plan.sample, with_types=True)[1]
    return column_types(plan.sample)


def _plan_summary(plan: Plan, cfg: Config, cases: list[Case], unstable: set[str], ignored: list[str]) -> dict:
    return {
        "mode": plan.mode,
        "run": plan.invocation.template,
        "output": plan.output,
        "sample": str(plan.sample_path),
        "columns": cfg.columns or "all",
        "column_types": plan.sql["types"] if plan.sql is not None else _sample_types(plan),
        "auto_ignored_columns": sorted(unstable),
        "ignored_columns": ignored,
        "cases": dict(Counter(c.category for c in cases)),
        "notes": plan.notes,
    }


SQL_TOLERANCE = 1e-9


def _frame_server(plan: Plan, cfg: Config, warnings: list[str]):
    """For DataFrame functions: a server that imports the libraries once and forks each run.

    Returns (server, invocation rewriter), or None to run each case as its own process."""
    if plan.sql is None or not plan.sql.get("function") or cfg.no_network or os.name != "posix":
        return None
    libs = sorted(set(plan.sql.get("libraries") or []))
    if "pyspark" in libs or os.environ.get("FIXWITNESS_NO_SERVER"):
        return None
    from fixwitness.pyserve import Server
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH": plan.invocation.env.get("PYTHONPATH", ""),
           "PYTHONHASHSEED": "0", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC", "HOME": str(plan.work)}
    try:
        server = Server(plan.work, libs, env)
    except (OSError, RuntimeError) as exc:
        warnings.append(f"ran each case as its own process (the DataFrame server did not start: {exc})")
        return None

    def rewrite(inv):
        template = inv.template.replace(" -m fixwitness.pyrun ", f" -m fixwitness.pyserve {server.path} -- ", 1)
        return dataclasses.replace(inv, template=template, env={**inv.env, "FIXWITNESS_RUN_TIMEOUT": str(inv.timeout)})
    return server, rewrite


def _explain(plan: Plan, opts: CompareOptions, kept: dict, entries: list[dict], details: dict) -> dict:
    """Plain-English sentence, impact and evidence tables for each difference."""
    from fixwitness.explain import explain_case, input_phrase
    out = {}
    for e in entries:
        if e["status"] not in ("changed", "after-failed", "still-exploitable"):
            continue
        k = kept.get(e["id"])
        if k is not None:
            try:
                out[e["id"]] = explain_case(k["case"], k["original"], k["fix"], plan.output, plan.sample_format,
                                            plan.sql is not None, opts.tolerance or 1e-9)
                continue
            except Exception as exc:  # an explanation must never break a check
                out[e["id"]] = {"sentence": None, "impact": None, "error": f"no explanation: {exc}"}
        if e["status"] == "still-exploitable":
            out[e["id"]] = {"impact": "security", "sentence": f"The {e['family']} payload still works on the fix."}
        else:
            phrase = input_phrase(e["category"], e["column"], e["value"], plan.sql is not None)
            first = (details.get(e["id"]) or ["the output changes"])[0]
            out[e["id"]] = {"impact": "fails" if e["status"] == "after-failed" else "values",
                            "sentence": f"If {phrase}, {'the fix fails' if e['status'] == 'after-failed' else 'the output changes'} ({first[:120]})."}
    return out


def _accepted(cfg: Config) -> list[dict]:
    """The [[accept]] entries for this check (no target, or the target being checked)."""
    if not cfg.accept:
        return []
    here = [str(p) for p in (cfg.path, cfg.after) if p]
    out = []
    for a in cfg.accept:
        t = a.get("target")
        t_file = t.split(":", 1)[0].strip() if t else None
        t_func = t.split(":", 1)[1].strip().rstrip("()") if t and ":" in t else None
        if t is None or (any(h == t_file or h.endswith("/" + t_file) for h in here)
                         and (t_func is None or t_func == cfg.function)):
            out.append(a)
    return out


def _is_accepted(case: Case, accepted: list[dict]) -> bool:
    return any(a["category"] == case.category and (a.get("column") in (None, "", case.column)) for a in accepted)


SHRINK_SECONDS = 25
SHRINK_FINDINGS = 6


def _shrink_kept(plan: Plan, inv_b, inv_a, opts: CompareOptions, kept: dict, status: dict) -> None:
    """Make the first findings as small as possible (fewer rows), keeping the same difference."""
    from fixwitness.shrink import shrink_case
    deadline = time.time() + SHRINK_SECONDS
    counter = [0]

    def run_pair(content: bytes):
        counter[0] += 1
        d = plan.work / "shrink" / str(counter[0])
        b = run_side(inv_b, plan.before, d, content)
        a = run_side(inv_a, plan.after, d, content)
        shutil.rmtree(d, ignore_errors=True)
        return b, a

    for cid in sorted(kept)[:SHRINK_FINDINGS]:
        if time.time() > deadline:
            break
        k = kept[cid]
        try:
            got = shrink_case(k["case"], status.get(cid, "changed"), run_pair, lambda x, y: compare(x, y, opts)[0],
                              plan.sample_format, plan.sql is not None, deadline)
        except Exception:  # shrinking only makes the evidence smaller; it must never break a check
            got = None
        if got is not None:
            k["case"], k["original"], k["fix"] = got
            k["shrunk"] = True


def _source(side) -> str | None:
    """The code of one side: a file, or every .sql/.py file of a folder."""
    if side.script is None:
        return None
    p = (side.root / side.script) if side.root is not None else Path(side.script)
    try:
        if p.is_dir():
            return "\n".join(f.read_text(encoding="utf-8", errors="replace")
                             for f in sorted(p.rglob("*")) if f.suffix in (".sql", ".py"))
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def focus(plan: Plan, columns: list[str]) -> list[str]:
    """Columns named in the lines the change touched; their cases are kept first under the cap. For
    a dbt project, every column the changed models name counts (a filter the change moved around,
    such as `where deleted_at is null`, sits on a line the change did not touch)."""
    from fixwitness.cases import focus_columns
    found = focus_columns(_source(plan.before), _source(plan.after), columns)
    changed = (plan.inputs.get("dbt") or {}).get("changed_models") or []
    if changed:
        import difflib
        tables = set((plan.inputs.get("dbt") or {}).get("changed_tables") or [])
        edited, texts = [], []
        for name in changed:
            pair = []
            for side in (plan.before, plan.after):
                root = side.script if side.script is not None and Path(side.script).is_dir() else None
                f = Path(root) / f"{name}.sql" if root is not None else None
                pair.append(f.read_text(encoding="utf-8", errors="replace") if f is not None and f.is_file() else "")
            texts += pair
            for line in difflib.unified_diff(pair[0].splitlines(), pair[1].splitlines(), lineterm="", n=0):
                if line[:1] in "+-" and line[:3] not in ("+++", "---"):
                    edited.append(line[1:])
        in_scope = [c for c in columns if not tables or c.split(".", 1)[0] in tables]
        # Columns named on the lines the change edited come first; then every column the changed
        # models name (a filter the change moved around sits on a line it did not touch).
        for words in (set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", "\n".join(edited))),
                      set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", "\n".join(texts)))):
            found += [c for c in in_scope if c.rsplit(".", 1)[-1] in words and c not in found]
    return found


def _exact_types(plan: Plan) -> dict | None:
    """The exact column types dbt gave the seeds (written beside the compiled models), if any."""
    from fixwitness.sql import TYPES_FILE
    root = plan.before.script if plan.before is not None else None
    f = Path(root) / TYPES_FILE if root is not None and Path(root).is_dir() else None
    if f is None or not f.is_file():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("types") if "adapter" in data else data


def _apply_contracts(plan: Plan, cases: list[Case], contracts: list[dict], base: dict[str, bytes]) -> None:
    """Inputs that break the project's own dbt tests (a duplicate in a column tested unique, a NULL
    in a column tested not_null, a value outside accepted_values) are reviewed, not failed: the
    project declares that such data does not occur. A test the sample itself breaks is not used."""
    from fixwitness.sql import contract_breaks, read_bundle
    broken_by_sample = contract_breaks(base, contracts)
    used = [i for i in range(len(contracts)) if i not in broken_by_sample]
    if broken_by_sample:
        plan.notes.append("dbt tests not used as rules, because the sample itself breaks them: "
                          + "; ".join(contracts[i]["from"] for i in sorted(broken_by_sample)))
    if not used:
        return
    rules = [contracts[i] for i in used]
    moved: dict[str, int] = {}
    for c in cases:
        if c.kind != "valid":
            continue
        try:
            tables, _ = read_bundle(c.content)
        except Exception:
            continue
        hit = contract_breaks(tables, rules)
        if hit:
            c.kind = "review"
            for i in hit:
                moved[rules[i]["from"]] = moved.get(rules[i]["from"], 0) + 1
    plan.notes.append(f"the project's dbt tests are used as rules on the input tables ({len(rules)}: "
                      + ", ".join(f"{r['table']}.{'+'.join(r['columns'])} {r['test']}" for r in rules[:12])
                      + (", ..." if len(rules) > 12 else "") + ")"
                      + (f"; {sum(1 for c in cases if c.kind == 'review')} inputs break one and are reviewed, not "
                         f"failed" if moved else "; no generated input breaks them"))
    plan.sql["contracts_moved"] = moved


def _cases(plan: Plan, cfg: Config) -> list[Case]:
    if plan.sql is not None:
        cols = [f"{t}.{c}" for t, kinds in plan.sql["types"].items() for c in kinds]
        contracts = list(plan.sql.get("contracts") or [])
        unique = {(c["table"], c["columns"][0].lower()) for c in contracts if c["test"] == "unique" and len(c["columns"]) == 1}
        exact = _exact_types(plan)
        tables, links = link_tables(plan.sql["tables"], plan.sql["types"], cfg.rows, unique, exact)
        if links and not any(n.startswith("the sample's tables did not join") for n in plan.notes):
            plan.notes.append("the sample's tables did not join on these keys, so the cases use matching keys "
                              "(the tables as given are case 000): " + ", ".join(links))
        try:
            cases = generate_sql_cases(tables, plan.sql["types"], cfg.columns, cfg.rows, cfg.max_cases,
                                       cfg.seed, cfg.review, plan.sql["incident_tables"], focus(plan, cols), exact)
        except ValueError as exc:
            raise PlanError(str(exc)) from exc
        if links:  # the tables exactly as given still run, first
            from fixwitness.sql import make_bundle
            given = Case(id="000", category="file-structure", kind="valid", column=None,
                         value="<tables as given>", content=make_bundle(plan.sql["tables"], plan.sql["types"]))
            cases = [given] + cases[: max(0, cfg.max_cases - 1)]
            for i, c in enumerate(cases):
                c.id = f"{i:03d}"
        if contracts:
            _apply_contracts(plan, cases, contracts, tables)
        return cases
    try:
        if plan.sample_format == "json":
            paths = list(json_paths(parse_json_sample(plan.sample)[1]))
            return generate_json_cases(plan.sample, cfg.columns, cfg.rows, cfg.max_cases, cfg.seed, cfg.review,
                                       str(plan.canary_dir), cfg.attacks, plan.incident,
                                       focus(plan, paths))
        if plan.sample_format == "parquet":
            return generate_parquet_cases(plan.sample, cfg.columns, cfg.rows, cfg.max_cases, cfg.seed, cfg.review,
                                          plan.incident)
    except SampleError as exc:
        raise PlanError(str(exc)) from exc
    header = list(column_types(plan.sample))
    return generate_cases(plan.sample, cfg.columns, cfg.rows, cfg.max_cases, cfg.seed, cfg.review,
                          str(plan.canary_dir), cfg.attacks, plan.incident, focus(plan, header))


def dry_run(cfg: Config) -> dict:
    """Resolve everything and run only the probes; no full comparison."""
    with build_plan(cfg) as plan:
        opts = CompareOptions(mode=plan.output, ignore_patterns=_compile_patterns(cfg.ignore_patterns))
        unstable, warnings, _ = _baseline(plan, opts, cfg.auto_ignore_unstable)
        cases = _cases(plan, cfg)
        summary = _plan_summary(plan, cfg, cases, unstable, cfg.ignore_columns)
        summary["incident"] = plan.incident_path.name if plan.incident_path else None
        summary["attacks"] = cfg.attacks and plan.sql is None
        summary["inputs"] = plan.inputs
        summary["warnings"] = warnings
        return summary


def run_check(cfg: Config) -> dict:
    with build_plan(cfg) as plan:
        return _run(plan, cfg)


def _run(plan: Plan, cfg: Config) -> dict:
    if plan.sql is not None:
        # A SQL query has no injectable input, so attacks don't apply. Sums may be added in another
        # order by an equivalent query, so numbers are compared with a small relative tolerance.
        cfg = dataclasses.replace(cfg, attacks=False, tolerance=cfg.tolerance or SQL_TOLERANCE)
    opts = CompareOptions(mode=plan.output, ignore_columns=set(cfg.ignore_columns),
                          ignore_patterns=_compile_patterns(cfg.ignore_patterns),
                          tolerance=cfg.tolerance, unordered=cfg.unordered,
                          columns_by_name=plan.sql is not None and not cfg.function and not cfg.sql_ordered)
    unstable, warnings, baseline = _baseline(plan, opts, cfg.auto_ignore_unstable)
    if unstable:
        opts.ignore_columns |= unstable
        warnings.append(f"ignored column(s) {', '.join(sorted(unstable))}: they change between two runs of the "
                        "original on the same input")
    expected_opts = dataclasses.replace(opts, ignore_columns=opts.ignore_columns | set(cfg.expect_change)) \
        if cfg.expect_change else None
    cases = _cases(plan, cfg)
    accepted = _accepted(cfg)
    if accepted:
        cases = [dataclasses.replace(c, kind="review") if c.kind == "valid" and _is_accepted(c, accepted) else c
                 for c in cases]

    inv_b, inv_a, server = plan.invocation, plan.fix_invocation, _frame_server(plan, cfg, warnings)
    if server is not None:
        inv_b, inv_a = server[1](inv_b), server[1](inv_a)

    def one(case: Case):
        case_dir = plan.work / "cases" / case.id
        b = run_side(inv_b, plan.before, case_dir, case.content, case.canary, case.oracle, plan.canary_dir)
        a = run_side(inv_a, plan.after, case_dir, case.content, case.canary, case.oracle, plan.canary_dir)
        again = None
        if cfg.auto_ignore_unstable and case.kind != "attack" and b.ok and a.ok and b.output is not None \
                and a.output is not None \
                and compare(b.output, a.output, opts)[0] == "changed":
            # A difference counts only if the original gives the same output when run again on this
            # input: ties in ORDER BY or row_number(), or set order, can make it differ by itself.
            again = run_side(inv_b, plan.before, case_dir / "again", case.content, case.canary, case.oracle,
                             plan.canary_dir)
        shutil.rmtree(case_dir, ignore_errors=True)
        rows = None
        if case.kind == "valid" and b.ok and b.output is not None and plan.output == "csv" and plan.sql is None \
                and plan.sample_format == "csv":
            n_in, n_out = _data_rows(case.content), _data_rows(b.output)
            if n_in is not None and n_out is not None:
                rows = (n_in, n_out)
        entry, details = _evaluate(case, b, a, opts, expected_opts)
        if again is not None and entry["status"] == "changed" and again.ok and again.output is not None:
            st, det = compare(b.output, again.output, opts)
            if st == "changed":
                # The columns that change from run to run on this input are left out of this
                # input's comparison; what still differs is the change's.
                cols, problem = unstable_columns(b.output, again.output)
                left = compare(b.output, a.output, dataclasses.replace(opts, ignore_columns=opts.ignore_columns | cols)) \
                    if cols and not problem else ("unstable", [])
                if left[0] == "changed":
                    details = left[1] + [f"left out on this input because the original's own output changes from run "
                                         f"to run: {', '.join(sorted(cols)[:6])}"]
                else:
                    entry["status"] = "unstable"
                    details = ["the original gave a different output when run again on this input, so the "
                               "difference is not the change's: " + "; ".join(det[:2])]
        if entry["status"] in ("changed", "after-failed") and entry["kind"] != "attack":
            kept[case.id] = {"case": case, "original": b, "fix": a}
        return (entry, details), rows

    kept: dict[str, dict] = {}
    workers = cfg.workers or min(8, os.cpu_count() or 2)
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(one, cases))
        if kept and cfg.shrink:
            _shrink_kept(plan, inv_b, inv_a, opts, kept, {e["id"]: e["status"] for (e, _), _ in results})
    finally:
        if server is not None:
            server[0].stop()
    evaluated = [r for r, _ in results]
    row_pairs = [rows for _, rows in results if rows is not None]
    preserves_rows = len(row_pairs) >= 5 and all(i == o for i, o in row_pairs)
    incident, incident_details = _check_incident(plan, opts, baseline, preserves_rows)

    entries = [e for e, _ in evaluated]
    detail_map = {e["id"]: d for e, d in evaluated if d}
    attacks = [e for e in entries if e["kind"] == "attack"]
    valid = [e for e in entries if e["kind"] == "valid"]
    review = [e for e in entries if e["kind"] == "review"]

    reproduced = any(e["before"]["exploited"] for e in attacks)
    still_open = [e for e in attacks if e["status"] == "still-exploitable"]
    changed = [e for e in valid if e["status"] in ("changed", "after-failed")]
    identical = [e for e in valid if e["status"] in ("identical", "same-data")]
    expected = [e for e in valid + review if e["status"] == "expected-change"]
    identical += [e for e in valid if e["status"] == "expected-change"]  # nothing but the expected change
    not_comparable = [e for e in valid if e["status"] == "not-comparable"]
    unstable_cases = [e for e in valid + review if e["status"] == "unstable"]
    review_diffs = [e for e in review if e["status"] in ("changed", "after-failed")]

    reasons = []
    if incident and incident["status"] == "still-failing":
        reasons.append(f"the fix still fails on the incident input {incident['file']}")
    if incident and incident["status"] == "resolved-incorrectly":
        reasons.append(f"the fix processes {incident['file']} but {incident_details['problems'][0]}")
    if still_open:
        fams = sorted({e["family"] for e in still_open})
        reasons.append(f"the fix is still exploitable by {len(still_open)} of {len(attacks)} payloads "
                       f"({', '.join(fams)})")
    if changed:
        reasons.append(f"the fix changes more than {', '.join(cfg.expect_change)}: other output differs on "
                       f"{len(changed)} valid inputs" if cfg.expect_change else
                       f"the fix changes output on {len(changed)} valid inputs")
    if not identical and not changed:
        reasons.append("no valid input could be compared (the original failed on all of them)")
    incident_failed = bool(incident and incident["status"] in ("still-failing", "resolved-incorrectly"))
    verdict = "FAIL" if (still_open or changed or incident_failed) else ("INCONCLUSIVE" if not identical else "PASS")
    if cfg.expect_change:
        cols = ", ".join(cfg.expect_change)
        if expected and verdict == "PASS":
            notes_extra = [f"the expected change ({cols}) appears on {len(expected)} inputs, and nothing else "
                           f"changes on any of the {len(identical)} compared inputs"]
        elif not expected and verdict != "FAIL":
            verdict = "INCONCLUSIVE"
            reasons.append(f"no input changed {cols}: the change you expect did not show")
            notes_extra = []
        else:
            notes_extra = []
    else:
        notes_extra = []
    if cfg.attacks and not reproduced:
        warnings.append("no built-in payload exploited the original, so 'hole closed' could not be demonstrated")
    if incident and incident["status"] == "not-reproduced":
        warnings.append(f"the original did not fail on {incident['file']}, so 'incident resolved' could not be "
                        "demonstrated")
    claims = ([reproduced] if cfg.attacks else []) + ([incident["status"] == "resolved"] if incident else [])
    if not_comparable:
        warnings.append(f"{len(not_comparable)} valid inputs could not be compared because the original failed on them")
    if unstable_cases:
        warnings.append(f"{len(unstable_cases)} inputs were left out: on them the original's own output changes from "
                        f"run to run (for example ties in ORDER BY or row_number()), so a difference there is not "
                        f"the change's (cases {', '.join(e['id'] for e in unstable_cases[:8])})")

    score = confidence(verdict, len(identical), all(claims))
    families = sorted({e["family"] for e in attacks if e["before"]["exploited"]})
    core = {
        "tool": {"name": "fixwitness", "version": __version__},
        "inputs": plan.inputs,
        "config": {
            "mode": plan.mode,
            "run": plan.invocation.template,
            "run_after": plan.after_invocation.template if plan.after_invocation else None,
            "columns": cfg.columns,
            "output": plan.output,
            "review": sorted(cfg.review),
            "accepted": accepted or None,
            "attacks": cfg.attacks,
            "ignore_columns": sorted(cfg.ignore_columns),
            "expect_change": sorted(cfg.expect_change) or None,
            "contracts": sorted(plan.sql["contracts_moved"]) if plan.sql is not None and plan.sql.get("contracts_moved") else None,
            "auto_ignored_columns": sorted(unstable),
            "ignore_patterns": list(cfg.ignore_patterns),
            "tolerance": cfg.tolerance,
            "unordered": cfg.unordered,
            "sql": {"engine": plan.sql["engine"], "dbt": cfg.dbt, "ordered": cfg.sql_ordered,
                    "dialect": cfg.dialect, "outputs": plan.sql["outputs"]}
                   if plan.sql is not None and not cfg.function else None,
            "frame": {"function": cfg.function, "libraries": plan.sql["libraries"], "ordered": cfg.sql_ordered}
                     if plan.sql is not None and cfg.function else None,
            "max_cases": cfg.max_cases,
            "rows": cfg.rows,
            "seed": cfg.seed,
        },
        "verdict": verdict,
        "reasons": reasons,
        "confidence": score,
        "incident": incident,
        "security": {
            "checked": cfg.attacks,
            "payloads": len(attacks),
            "original_exploited": sum(1 for e in attacks if e["before"]["exploited"]),
            "fix_exploited": len(still_open),
            "finding_reproduced": reproduced,
            "families_reproduced": families,
            "hole_closed": not still_open,
        },
        "behavior": {
            "valid_inputs": len(valid), "identical": len(identical), "changed": len(changed),
            "not_comparable": len(not_comparable), "review_inputs": len(review),
            "review_differences": len(review_diffs),
            "expected_change": len(expected),
            "unstable": len(unstable_cases),
        },
        "cases": [
            {k: e[k] for k in ("id", "category", "kind", "column", "family", "status")}
            | {"before_exploited": e["before"]["exploited"], "after_exploited": e["after"]["exploited"]}
            for e in entries
        ],
    }
    proof_id = hashlib.sha256(_canonical(core)).hexdigest()
    explained = _explain(plan, opts, kept, entries, detail_map)
    REPRO[proof_id] = {
        "kept": {k: kept[k] for k in sorted(kept)[:MAX_REPROS]},
        "invocations": (plan.invocation, plan.fix_invocation), "sides": (plan.before, plan.after),
        "mode": plan.mode, "base_commit": plan.inputs.get("base_commit"), "repo": plan.replay.get("repo"),
        "tables": plan.sql is not None,
        "explained": explained,
    }
    return {
        "proof_id": proof_id,
        **core,
        "notes": plan.notes + notes_extra,
        "warnings": warnings,
        "incident_details": incident_details,
        "differences": [
            {"id": e["id"], "category": e["category"], "kind": e["kind"], "column": e["column"],
             "family": e["family"], "value": e["value"], "status": e["status"],
             "explanation": explained.get(e["id"], {}).get("sentence"),
             "impact": explained.get(e["id"], {}).get("impact"),
             "shrunk": bool(kept.get(e["id"], {}).get("shrunk")),
             "details": detail_map.get(e["id"], [])}
            for e in entries if e["status"] in ("changed", "after-failed", "still-exploitable")
        ][:50],
        # Inputs on which only the expected columns changed: what the fix does, shown by example.
        "expected_changes": [
            {"id": e["id"], "category": e["category"], "column": e["column"], "value": e["value"],
             "details": detail_map.get(e["id"], [])[:6]}
            for e in entries if e["status"] == "expected-change"
        ][:10] if cfg.expect_change else None,
        "categories": {k: (CATEGORY_DESCRIPTIONS | JSON_CATEGORY_DESCRIPTIONS).get(k, k)
                       for k in sorted({e["category"] for e in entries})},
        "limitations": LIMITATIONS,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replay": plan.replay | {
            "settings": {
                "columns": cfg.columns, "review": cfg.review, "output": cfg.output, "max_cases": cfg.max_cases,
                "accept": cfg.accept,
                "attacks": cfg.attacks,
                "rows": cfg.rows, "seed": cfg.seed, "ignore_columns": cfg.ignore_columns,
                "expect_change": cfg.expect_change,
                "ignore_patterns": cfg.ignore_patterns, "tolerance": cfg.tolerance, "unordered": cfg.unordered,
                "auto_ignore_unstable": cfg.auto_ignore_unstable, "timeout": cfg.timeout,
                "pass_env": cfg.pass_env, "allow_any_command": cfg.allow_any_command,
                "no_network": cfg.no_network,
                "engine": cfg.engine, "dbt": cfg.dbt, "sql_ordered": cfg.sql_ordered, "warehouse": cfg.warehouse,
                "dialect": cfg.dialect, "sql_outputs": cfg.sql_outputs,
                "function": cfg.function, "library": cfg.library,
            },
        },
    }


def replay(proof: dict, allow_any_command: bool | None = None) -> dict:
    """Re-run a proof from its recorded inputs and settings; report whether it reproduces."""
    rp = proof.get("replay") or {}
    settings = dict(rp.get("settings", {}))
    if allow_any_command is not None:
        settings["allow_any_command"] = allow_any_command
    problems: list[str] = []
    inputs = proof["inputs"]
    sql_tables = rp.get("tables")
    if sql_tables is not None:
        for group, label in (("tables", "table"), ("incident_tables", "incident table")):
            for name, path in (rp.get(group) or {}).items():
                p = Path(path)
                if not p.is_file() or sha256_file(p) != inputs[group][name]["sha256"]:
                    problems.append(f"{label} {name} is missing or has changed ({p.name})")
        if settings.get("engine") == "auto" and inputs.get("engine") in ("duckdb", "sqlite"):
            settings["engine"] = inputs["engine"]  # replay with the engine the proof used
    dbt_project = bool(rp.get("dbt_project"))
    if rp.get("mode") == "files" and dbt_project:
        for label in ("base_manifest", "manifest"):
            p = Path(rp.get(label, ""))
            if not p.is_file() or sha256_file(p) != inputs[label]["sha256"]:
                problems.append(f"{label.replace('_', ' ')} is missing or has changed ({p.name})")
        cfg_args = {"manifest": rp.get("manifest"), "base_manifest": rp.get("base_manifest"),
                    "incident_expected": rp.get("incident_expected")}
    elif rp.get("mode") == "files":
        for label in ("before", "after") + (() if sql_tables is not None else ("sample",)):
            p = Path(rp.get(label, ""))
            if not p.exists():
                problems.append(f"{label} file not found at {p}")
            elif sha256_file(p) != inputs[label]["sha256"]:
                problems.append(f"{label} file has changed since the proof was made ({p.name})")
        cfg_args = {"before": rp.get("before"), "after": rp.get("after"), "sample": rp.get("sample"),
                    "run": None if sql_tables is not None else rp.get("run"), "run_after": rp.get("run_after"),
                    "incident": rp.get("incident"), "incident_expected": rp.get("incident_expected")}
    elif rp.get("mode") == "git":
        repo = Path(rp.get("repo", ""))
        for item in inputs.get("changed", []):
            f = repo / item["path"]
            current = sha256_file(f) if f.is_file() else None
            if current != item["sha256"]:
                problems.append(f"{item['path']} has changed since the proof was made")
        if sql_tables is None and not dbt_project:
            s = Path(rp.get("sample", ""))
            if not s.is_file() or sha256_file(s) != inputs["sample"]["sha256"]:
                problems.append("the sample file is missing or has changed")
        cfg_args = {"path": rp.get("path"), "base": rp.get("base_commit"), "command": rp.get("command"),
                    "run": None if (rp.get("command") or sql_tables is not None or dbt_project) else rp.get("run"),
                    "sample": None if dbt_project else rp.get("sample"),
                    "incident": rp.get("incident"), "incident_expected": rp.get("incident_expected")}
    else:
        return {"reproduced": False, "problems": ["the proof has no replay information"]}
    if rp.get("incident"):
        p = Path(rp["incident"])
        if not p.is_file() or sha256_file(p) != inputs["incident"]["sha256"]:
            problems.append("the incident file is missing or has changed")
    if dbt_project and rp.get("dbt_tables"):
        cfg_args["tables"] = rp["dbt_tables"]
    if sql_tables is not None:
        cfg_args["tables"] = sql_tables
        cfg_args["incident_tables"] = rp.get("incident_tables")
    if problems:
        return {"reproduced": False, "problems": problems}
    cfg = Config(**{k: v for k, v in cfg_args.items() if v is not None},
                 **{k: v for k, v in settings.items() if v is not None},
                 base_dir=Path(rp.get("repo") or Path.cwd()))
    fresh = run_check(cfg)
    same = fresh["proof_id"] == proof["proof_id"]
    result = {"reproduced": same, "original_proof_id": proof["proof_id"], "replay_proof_id": fresh["proof_id"],
              "verdict": fresh["verdict"], "problems": []}
    if not same:
        if fresh["tool"]["version"] != proof["tool"]["version"]:
            result["problems"].append(f"fixwitness version differs ({proof['tool']['version']} -> "
                                      f"{fresh['tool']['version']})")
        old = {x["id"]: x for x in proof["cases"]}
        for x in fresh["cases"]:
            if old.get(x["id"]) != x:
                y = old.get(x["id"])
                result["problems"].append(f"case {x['id']} ({x['category']}): {y and y['status']} -> {x['status']}")
                if len(result["problems"]) >= 10:
                    break
    return result
