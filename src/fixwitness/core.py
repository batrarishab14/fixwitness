"""Run a check and build the proof record."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fixwitness import __version__
from fixwitness.cases import CATEGORY_DESCRIPTIONS, Case, column_types, generate_cases
from fixwitness.sql import generate_sql_cases
from fixwitness.compare import CompareOptions, compare, parse_rows, unstable_columns
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


def _evaluate(case: Case, before: RunResult, after: RunResult, opts: CompareOptions) -> tuple[dict, list[str]]:
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
    status = "still-failing" if not a_ok else ("resolved" if not b_ok else "not-reproduced")

    problems: list[str] = []
    if a_ok and plan.output == "csv":
        fix_rows, base_rows = parse_rows(a.output), parse_rows(baseline) if baseline else None
        if fix_rows is not None and base_rows is not None and fix_rows[:1] != base_rows[:1]:
            problems.append(f"its output columns {fix_rows[0] if fix_rows else []} differ from the original's "
                            f"{base_rows[0] if base_rows else []}")
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

    details = {"original": None if b_ok else why(b), "fix": None if a_ok else why(a), "problems": problems}
    checks = ["processes it"] + (["same columns"] if baseline and plan.output == "csv" else []) \
        + (["one row per input row"] if preserves_rows else []) \
        + (["expected output"] if plan.incident_expected is not None else [])
    return {"file": plan.incident_path.name, "status": status, "checks": checks}, details


def _plan_summary(plan: Plan, cfg: Config, cases: list[Case], unstable: set[str], ignored: list[str]) -> dict:
    return {
        "mode": plan.mode,
        "run": plan.invocation.template,
        "output": plan.output,
        "sample": str(plan.sample_path),
        "columns": cfg.columns or "all",
        "column_types": plan.sql["types"] if plan.sql is not None else column_types(plan.sample),
        "auto_ignored_columns": sorted(unstable),
        "ignored_columns": ignored,
        "cases": dict(Counter(c.category for c in cases)),
        "notes": plan.notes,
    }


SQL_TOLERANCE = 1e-9


def _cases(plan: Plan, cfg: Config) -> list[Case]:
    if plan.sql is not None:
        try:
            return generate_sql_cases(plan.sql["tables"], plan.sql["types"], cfg.columns, cfg.rows, cfg.max_cases,
                                      cfg.seed, cfg.review, plan.sql["incident_tables"])
        except ValueError as exc:
            raise PlanError(str(exc)) from exc
    return generate_cases(plan.sample, cfg.columns, cfg.rows, cfg.max_cases, cfg.seed, cfg.review,
                          str(plan.canary_dir), cfg.attacks, plan.incident)


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
                          tolerance=cfg.tolerance, unordered=cfg.unordered)
    unstable, warnings, baseline = _baseline(plan, opts, cfg.auto_ignore_unstable)
    if unstable:
        opts.ignore_columns |= unstable
        warnings.append(f"ignored column(s) {', '.join(sorted(unstable))}: they change between two runs of the "
                        "original on the same input")
    cases = _cases(plan, cfg)

    def one(case: Case):
        case_dir = plan.work / "cases" / case.id
        b = run_side(plan.invocation, plan.before, case_dir, case.content, case.canary, case.oracle, plan.canary_dir)
        a = run_side(plan.fix_invocation, plan.after, case_dir, case.content, case.canary, case.oracle, plan.canary_dir)
        shutil.rmtree(case_dir, ignore_errors=True)
        rows = None
        if case.kind == "valid" and b.ok and b.output is not None and plan.output == "csv" and plan.sql is None:
            n_in, n_out = _data_rows(case.content), _data_rows(b.output)
            if n_in is not None and n_out is not None:
                rows = (n_in, n_out)
        return _evaluate(case, b, a, opts), rows

    workers = cfg.workers or min(8, os.cpu_count() or 2)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, cases))
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
    not_comparable = [e for e in valid if e["status"] == "not-comparable"]
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
        reasons.append(f"the fix changes output on {len(changed)} valid inputs")
    if not identical and not changed:
        reasons.append("no valid input could be compared (the original failed on all of them)")
    incident_failed = bool(incident and incident["status"] in ("still-failing", "resolved-incorrectly"))
    verdict = "FAIL" if (still_open or changed or incident_failed) else ("INCONCLUSIVE" if not identical else "PASS")
    if cfg.attacks and not reproduced:
        warnings.append("no built-in payload exploited the original, so 'hole closed' could not be demonstrated")
    if incident and incident["status"] == "not-reproduced":
        warnings.append(f"the original did not fail on {incident['file']}, so 'incident resolved' could not be "
                        "demonstrated")
    claims = ([reproduced] if cfg.attacks else []) + ([incident["status"] == "resolved"] if incident else [])
    if not_comparable:
        warnings.append(f"{len(not_comparable)} valid inputs could not be compared because the original failed on them")

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
            "attacks": cfg.attacks,
            "ignore_columns": sorted(cfg.ignore_columns),
            "auto_ignored_columns": sorted(unstable),
            "ignore_patterns": list(cfg.ignore_patterns),
            "tolerance": cfg.tolerance,
            "unordered": cfg.unordered,
            "sql": {"engine": plan.sql["engine"], "dbt": cfg.dbt, "ordered": cfg.sql_ordered}
                   if plan.sql is not None else None,
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
        },
        "cases": [
            {k: e[k] for k in ("id", "category", "kind", "column", "family", "status")}
            | {"before_exploited": e["before"]["exploited"], "after_exploited": e["after"]["exploited"]}
            for e in entries
        ],
    }
    proof_id = hashlib.sha256(_canonical(core)).hexdigest()
    return {
        "proof_id": proof_id,
        **core,
        "notes": plan.notes,
        "warnings": warnings,
        "incident_details": incident_details,
        "differences": [
            {"id": e["id"], "category": e["category"], "kind": e["kind"], "column": e["column"],
             "family": e["family"], "value": e["value"], "status": e["status"],
             "details": detail_map.get(e["id"], [])}
            for e in entries if e["status"] in ("changed", "after-failed", "still-exploitable")
        ][:50],
        "categories": {k: CATEGORY_DESCRIPTIONS[k] for k in sorted({e["category"] for e in entries})},
        "limitations": LIMITATIONS,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replay": plan.replay | {
            "settings": {
                "columns": cfg.columns, "review": cfg.review, "output": cfg.output, "max_cases": cfg.max_cases,
                "attacks": cfg.attacks,
                "rows": cfg.rows, "seed": cfg.seed, "ignore_columns": cfg.ignore_columns,
                "ignore_patterns": cfg.ignore_patterns, "tolerance": cfg.tolerance, "unordered": cfg.unordered,
                "auto_ignore_unstable": cfg.auto_ignore_unstable, "timeout": cfg.timeout,
                "pass_env": cfg.pass_env, "allow_any_command": cfg.allow_any_command,
                "no_network": cfg.no_network,
                "engine": cfg.engine, "dbt": cfg.dbt, "sql_ordered": cfg.sql_ordered,
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
        if settings.get("engine") == "auto" and inputs.get("engine"):
            settings["engine"] = inputs["engine"]  # replay with the engine the proof used
    if rp.get("mode") == "files":
        for label in ("before", "after") + (() if sql_tables is not None else ("sample",)):
            p = Path(rp.get(label, ""))
            if not p.is_file():
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
        if sql_tables is None:
            s = Path(rp.get("sample", ""))
            if not s.is_file() or sha256_file(s) != inputs["sample"]["sha256"]:
                problems.append("the sample file is missing or has changed")
        cfg_args = {"path": rp.get("path"), "base": rp.get("base_commit"), "command": rp.get("command"),
                    "run": None if (rp.get("command") or sql_tables is not None) else rp.get("run"),
                    "sample": rp.get("sample"),
                    "incident": rp.get("incident"), "incident_expected": rp.get("incident_expected")}
    else:
        return {"reproduced": False, "problems": ["the proof has no replay information"]}
    if rp.get("incident"):
        p = Path(rp["incident"])
        if not p.is_file() or sha256_file(p) != inputs["incident"]["sha256"]:
            problems.append("the incident file is missing or has changed")
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
