"""Human-readable summaries of a proof record (Markdown, for terminals and pull requests)."""

from __future__ import annotations

import json
from pathlib import Path


def _mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _clip(text: str | None, limit: int = 90) -> str:
    if not text:
        return "no detail"
    line = [x for x in text.strip().splitlines() if x.strip()][-1] if text.strip() else text
    line = line.replace("|", "/").strip()
    return line if len(line) <= limit else line[: limit - 3] + "..."


def _what(proof: dict) -> str:
    inp = proof["inputs"]
    if inp.get("mode") == "git":
        target = f"`{inp['target']}`" if inp.get("target") else "your command"
        files = ", ".join(f"`{c['path']}`" for c in inp["changed"][:5])
        more = f" and {len(inp['changed']) - 5} more" if len(inp["changed"]) > 5 else ""
        return (f"{target}: commit `{inp['base_commit'][:12]}` (original) vs working tree (fix); "
                f"changed: {files}{more}")
    if "base_manifest" in inp:
        return f"dbt manifest `{inp['base_manifest']['name']}` (original) vs `{inp['manifest']['name']}` (fix)"
    return f"`{inp['before']['name']}` (original) vs `{inp['after']['name']}` (fix)"


def markdown(proof: dict, proof_file: str | None = None) -> str:
    v = proof["verdict"]
    conf = proof["confidence"]
    sec = proof["security"]
    beh = proof["behavior"]
    lines = [f"## fixwitness: PASS, confidence {conf['score']}/100 ({conf['level']})" if v == "PASS"
             else f"## fixwitness: {v}", ""]
    run_after = proof["config"].get("run_after")
    inp = proof["inputs"]
    if "tables" in inp:
        tables = ", ".join(f"`{n}` ({t['name']})" for n, t in inp["tables"].items())
        sql = proof["config"].get("sql") or {}
        extra = (f", written for {sql['dialect']}" if sql.get("dialect") else "") + \
                (f", outputs {', '.join(f'`{o}`' for o in sql['outputs'])}" if sql.get("outputs") else "")
        frame = proof["config"].get("frame")
        if frame:
            libs = frame["libraries"]
            lib = libs[0] if libs[0] == libs[1] else f"{libs[0]} (original) and {libs[1]} (fix)"
            lines.append(f"{_what(proof)}, Python function `{frame['function']}()` on {lib} DataFrames, tables {tables}")
        elif inp.get("dbt"):
            dbt = inp["dbt"]
            lines.append(f"{_what(proof)}. dbt project: changed {', '.join(f'`{m}`' for m in dbt['changed_models'])}; "
                         f"compared {', '.join(f'`{m}`' for m in dbt['compared'])}; SQL on "
                         f"{inp.get('engine', 'sqlite')}{extra.split(', outputs')[0]}; tables {tables}")
        else:
            lines.append(f"{_what(proof)}, SQL on {inp.get('engine', 'sqlite')}{extra}, tables {tables}")
    else:
        lines.append(f"{_what(proof)}, sample `{inp['sample']['name']}`, run `{proof['config']['run']}`"
                     + (f" (fix: `{run_after}`)" if run_after else ""))
    lines += ["", "| Check | Result |", "|---|---|"]
    inc = proof.get("incident")
    if inc:
        det = proof.get("incident_details") or {}
        if inc["status"] == "resolved":
            text = (f"PASS: the original failed on `{inc['file']}` ({_clip(det.get('original'))}); "
                    + ("the fix gives the expected output" if "expected output" in inc.get("checks", [])
                       else "the fix processes it"))
        elif inc["status"] == "still-failing":
            text = f"FAIL: the fix still fails on `{inc['file']}` ({_clip(det.get('fix'))})"
        elif inc["status"] == "resolved-incorrectly":
            text = (f"FAIL: the fix processes `{inc['file']}`, but "
                    + "; ".join(_clip(p, 160) for p in det.get("problems", [])))
        else:
            text = f"PASS: the fix processes `{inc['file']}` (note: the original did not fail on it either)"
        lines.append(f"| Incident resolved | {text} |")
    if sec.get("checked", True):
        fams = f": {', '.join(sec['families_reproduced'])}" if sec.get("families_reproduced") else ""
        lines.append(f"| Hole closed | {_mark(sec['hole_closed'])}: {sec['fix_exploited']} of {sec['payloads']} attack "
                     f"payloads worked on the fix ({sec['original_exploited']} worked on the original{fams}) |")
    else:
        lines.append("| Security | not checked (attack payloads turned off) |")
    same = beh["changed"] == 0 and beh["identical"] > 0
    lines.append(f"| Data unchanged | {_mark(same)}: {beh['identical']} of {beh['identical'] + beh['changed']} "
                 f"comparable valid inputs give the same output |")
    if proof["config"].get("expect_change"):
        cols = ", ".join(f"`{c}`" for c in proof["config"]["expect_change"])
        lines.append(f"| Expected change | {beh.get('expected_change', 0)} inputs changed only {cols} |")
    if beh["not_comparable"]:
        lines.append(f"| Not comparable | {beh['not_comparable']} valid inputs made the original fail too |")
    if beh["review_inputs"]:
        acc = proof["config"].get("accepted") or []
        what = ", ".join(proof["config"]["review"] + [f"{a['category']}" + (f" in {a['column']}" if a.get("column") else "")
                                                     + " (marked as intended)" for a in acc]
                         + ([f"inputs that break your dbt tests ({'; '.join(proof['config']['contracts'][:4])})"]
                            if proof["config"].get("contracts") else []))
        lines.append(f"| Needs review | {beh['review_differences']} of {beh['review_inputs']} inputs in review "
                     f"categories ({what}) differ |")
    lines.append("")
    if proof["reasons"]:
        lines += ["**Why:** " + "; ".join(proof["reasons"]) + ".", ""]
    for w in proof.get("warnings", []):
        lines.append(f"- Note: {w}")
    if proof.get("warnings"):
        lines.append("")

    diffs = [d for d in proof["differences"] if d["kind"] != "review"][:8]
    if diffs:
        from fixwitness.explain import IMPACTS
        lines += ["**What could go wrong:**", ""]
        for d in diffs:
            label = f"still exploitable ({d['family']})" if d["status"] == "still-exploitable" else d["status"]
            impact = IMPACTS.get(d.get("impact") or "", "Security" if d.get("impact") == "security" else None)
            if d.get("explanation"):
                lines.append(f"- {'**' + impact + '.** ' if impact else ''}{d['explanation']}")
                lines.append(f"  - case {d['id']}: `{d['category']}` input {d['value']!r} in `{d['column']}` ({label})"
                             + ("; input shrunk to the rows that show it" if d.get("shrunk") else ""))
            else:
                lines.append(f"- `{d['category']}` input {d['value']!r} in `{d['column']}`: {label}")
            for detail in d["details"][:2]:
                lines.append(f"  - {_clip(detail, 200)}")
        lines.append("")
    shown = proof.get("expected_changes") or []
    if shown:
        lines += ["**What the fix changes (as expected):**", ""]
        for e in shown[:3]:
            lines.append(f"- case {e['id']}: `{e['category']}` input {e['value']!r} in `{e['column']}`")
            for detail in e["details"][:3]:
                lines.append(f"  - {_clip(detail, 200)}")
        lines.append("")
    if v == "PASS":
        c = conf["components"]
        lines += [f"Confidence: {c['valid_inputs_identical']} valid inputs gave the same output, evidence strength "
                  f"{c['evidence_strength']} (rule of three), reproduction factor {c['reproduction_factor']}.", ""]
    lines.append(f"Proof ID `{proof['proof_id'][:16]}`"
                 + (f" · re-check with `fixwitness replay {proof_file}`" if proof_file else ""))
    return "\n".join(lines) + "\n"


def plan_text(summary: dict) -> str:
    lines = ["fixwitness plan (nothing has been compared yet)", ""]
    lines.append(f"  mode      {summary['mode']}")
    lines.append(f"  run       {summary['run']}")
    lines.append(f"  sample    {summary['sample']}")
    lines.append(f"  output    compared as {summary['output']}")
    if summary.get("incident"):
        lines.append(f"  incident  {summary['incident']} (the original should fail on it; the fix must handle it)")
    if summary.get("attacks") is False:
        lines.append("  attacks   off (repair mode)")
    ct = summary["column_types"]
    if ct and all(isinstance(v, dict) for v in ct.values()):  # SQL: one entry per table
        types = "; ".join(f"{t}: " + ", ".join(f"{k} ({v})" for k, v in cols.items()) for t, cols in ct.items())
    else:
        types = ", ".join(f"{k} ({v})" for k, v in ct.items())
    lines.append(f"  columns   {summary['columns'] if summary['columns'] != 'all' else 'all'}  [{types}]")
    if summary["auto_ignored_columns"]:
        lines.append(f"  ignored   {', '.join(summary['auto_ignored_columns'])} (not deterministic in the original)")
    total = sum(summary["cases"].values())
    lines.append(f"  cases     {total}: " + ", ".join(f"{k} {n}" for k, n in sorted(summary["cases"].items())))
    if summary["inputs"].get("mode") == "git":
        lines.append(f"  original  commit {summary['inputs']['base_commit'][:12]}")
        lines.append("  changed   " + ", ".join(c["path"] for c in summary["inputs"]["changed"][:8]))
    for n in summary["notes"]:
        lines.append(f"  note      {n}")
    for w in summary.get("warnings", []):
        lines.append(f"  warning   {w}")
    return "\n".join(lines) + "\n"


def _command(inv, script: str | None, input_path: str, output_path: str) -> str:
    import shlex
    from fixwitness.runner import build_command
    cmd = build_command(inv.template, script, input_path, output_path, True, inv.require_script)
    text = shlex.join(cmd.argv) + (f" < {shlex.quote(input_path)}" if cmd.stdin_from_input else "") \
        + (f" > {shlex.quote(output_path)}" if cmd.output_from == "stdout" else "")
    env = " ".join(f"{k}={shlex.quote(v)}" for k, v in inv.env.items())
    return f"{env} {text}" if env else text


def write_repros(proof: dict, out_dir: Path) -> list[Path]:
    """For each difference: the input, both outputs and the commands that produce them."""
    import shlex
    import shutil
    from fixwitness.core import REPRO
    info = REPRO.get(proof["proof_id"])
    root = out_dir / "repro"
    shutil.rmtree(root, ignore_errors=True)
    if not info or not info["kept"]:
        return []
    by_id = {d["id"]: d for d in proof["differences"]}
    inv_b, inv_a = info["invocations"]
    side_b, side_a = info["sides"]
    written = []
    for cid, k in info["kept"].items():
        d = root / cid
        d.mkdir(parents=True, exist_ok=True)
        case, b, a = k["case"], k["original"], k["fix"]
        inp = d / f"input{inv_b.input_suffix}"
        inp.write_bytes(case.content)
        if info["tables"]:
            from fixwitness.sql import read_bundle
            tables, _ = read_bundle(case.content)
            for name, text in tables.items():
                (d / "tables").mkdir(exist_ok=True)
                (d / "tables" / f"{name}.csv").write_text(text, encoding="utf-8")
        outs = {}
        for label, r, inv in (("original", b, inv_b), ("fix", a, inv_a)):
            if r.ok and r.output is not None:
                outs[label] = d / f"{label}{inv.output_suffix}"
                outs[label].write_bytes(r.output)
            else:
                outs[label] = d / f"{label}_error.txt"
                err = r.stderr.decode("utf-8", "replace") if isinstance(r.stderr, bytes) else (r.stderr or "")
                outs[label].write_text((r.error or ("timed out" if r.timed_out else err) or "no output").strip()
                                       + "\n", encoding="utf-8")
        diff = by_id.get(cid, {})
        lines = [f"# Case {cid}: {diff.get('category', case.category)}", "",
                 f"- Input: `{inp.name}`" + (" (and each table under `tables/`)" if info["tables"] else "")
                 + (f", value {case.value!r} in `{case.column}`" if case.column else f", {case.value}"),
                 f"- Result: {diff.get('status', '?')}"]
        lines += [f"  - {x}" for x in diff.get("details", [])[:5]]
        lines += ["", "## Re-run each side", ""]
        tmp_b, tmp_a = d / f"rerun_original{inv_b.output_suffix}", d / f"rerun_fix{inv_a.output_suffix}"
        if info["mode"] == "git":
            inp, tmp_b, tmp_a = inp.resolve(), tmp_b.resolve(), tmp_a.resolve()
            wt = f"/tmp/fixwitness-original-{info['base_commit'][:12]}"
            lines += ["From the repository root (your working tree is the fix):", "", "```bash",
                      f"git worktree add {wt} {info['base_commit'][:12]}   # the original",
                      f"(cd {wt} && {_command(inv_b, str(side_b.script) if side_b.script else None, str(inp), str(tmp_b))})",
                      _command(inv_a, str(side_a.script) if side_a.script else None, str(inp), str(tmp_a)),
                      f"git worktree remove {wt}", "```"]
        else:
            lines += ["```bash", f"cd {shlex.quote(str(d))}",
                      _command(inv_b, str(side_b.script) if side_b.script else None, inp.name, tmp_b.name),
                      _command(inv_a, str(side_a.script) if side_a.script else None, inp.name, tmp_a.name), "```"]
        lines += ["", f"The outputs fixwitness saw are `{outs['original'].name}` and `{outs['fix'].name}`."]
        (d / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(d)
    return written


PROOF_SCHEMA = "https://raw.githubusercontent.com/batrarishab14/fixwitness/main/docs/proof.schema.json"


def write_outputs(proof: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ignore = out_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    proof_path = out_dir / "proof.json"
    record = {"$schema": PROOF_SCHEMA, **proof}  # the format, for tools that read proofs
    proof_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    repros = write_repros(proof, out_dir)
    text = markdown(proof, str(proof_path))
    if repros:
        text += (f"\nEach difference above has a runnable reproduction (its input, both outputs and the commands) "
                 f"in `{out_dir / 'repro'}/<case>/`.\n")
    (out_dir / "report.md").write_text(text, encoding="utf-8")
    try:
        from fixwitness.htmlreport import write_single
        write_single(proof, out_dir)
    except Exception as exc:  # the HTML page is a convenience; the proof and report.md are the record
        (out_dir / "report.html").write_text(f"<!doctype html><p>report.html could not be built: {exc}</p>",
                                             encoding="utf-8")
    return proof_path
