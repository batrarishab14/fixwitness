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
    if beh["not_comparable"]:
        lines.append(f"| Not comparable | {beh['not_comparable']} valid inputs made the original fail too |")
    if beh["review_inputs"]:
        lines.append(f"| Needs review | {beh['review_differences']} of {beh['review_inputs']} inputs in review "
                     f"categories ({', '.join(proof['config']['review'])}) differ |")
    lines.append("")
    if proof["reasons"]:
        lines += ["**Why:** " + "; ".join(proof["reasons"]) + ".", ""]
    for w in proof.get("warnings", []):
        lines.append(f"- Note: {w}")
    if proof.get("warnings"):
        lines.append("")

    diffs = [d for d in proof["differences"] if d["kind"] != "review"][:8]
    if diffs:
        lines += ["**What changed (first examples):**", ""]
        for d in diffs:
            label = f"still exploitable ({d['family']})" if d["status"] == "still-exploitable" else d["status"]
            lines.append(f"- `{d['category']}` input {d['value']!r} in `{d['column']}`: {label}")
            for detail in d["details"][:3]:
                lines.append(f"  - {detail}")
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


def write_outputs(proof: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ignore = out_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    proof_path = out_dir / "proof.json"
    proof_path.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(markdown(proof, str(proof_path)), encoding="utf-8")
    return proof_path
