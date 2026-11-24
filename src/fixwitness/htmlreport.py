"""report.html: one self-contained page for everyone who decides on a change.

Read top to bottom, the page answers in order:
- the decision (safe to merge, don't merge yet, needs a look), for whoever signs off;
- what could go wrong, in plain sentences with an impact label, for product owners;
- the evidence: the smallest input that shows each difference and both outputs side by side,
  with the commands to reproduce it, for the developer;
- how it was checked: inputs by result and by kind, engine, notes and limits, for the architect.

No external files: it opens from disk, in CI artifacts and in the local web app.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from fixwitness.explain import IMPACTS, decision

E = html.escape

CSS = """
:root{--bg:#f4f6f9;--surface:#fff;--ink:#18212f;--muted:#5a6678;--rule:#d9dfe7;--soft:#eef1f5;
--pass:#1d7a4e;--pass-bg:#e5f3ec;--fail:#b3261e;--fail-bg:#fbe9e7;--review:#8a5a00;--review-bg:#fbf1dc;
--accent:#2c58b5;--mark:#fff1a8;--mark-ink:#18212f;--serif:"Iowan Old Style","Charter","Palatino Linotype",
"Book Antiqua",Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0d131b;--surface:#141c27;--ink:#e3e8ef;
--muted:#97a3b4;--rule:#273344;--soft:#1a2431;--pass:#55c690;--pass-bg:#12291f;--fail:#f07a72;--fail-bg:#2e1715;
--review:#e2b54a;--review-bg:#2b2310;--accent:#86a9f3;--mark:#5a4b10;--mark-ink:#fff6cf}}
:root[data-theme=dark]{--bg:#0d131b;--surface:#141c27;--ink:#e3e8ef;--muted:#97a3b4;--rule:#273344;--soft:#1a2431;
--pass:#55c690;--pass-bg:#12291f;--fail:#f07a72;--fail-bg:#2e1715;--review:#e2b54a;--review-bg:#2b2310;
--accent:#86a9f3;--mark:#5a4b10;--mark-ink:#fff6cf}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans)}
a{color:var(--accent)}code,pre,.mono{font-family:var(--mono);font-size:.86em}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 64px}
.top{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;color:var(--muted);font-size:13px}
.top b{color:var(--ink);font-weight:600}
.decision{margin:18px 0 26px;padding:26px 28px;border-radius:14px;background:var(--surface);border:1px solid var(--rule);
border-left:8px solid var(--tone)}
.decision h1{font:600 clamp(26px,4.2vw,40px)/1.12 var(--serif);margin:0 0 8px;letter-spacing:-.01em}
.decision p{margin:0;color:var(--muted);max-width:72ch}
.tone-pass{--tone:var(--pass)}.tone-fail{--tone:var(--fail)}.tone-review{--tone:var(--review)}
h2{font:600 20px/1.3 var(--sans);margin:34px 0 10px}h3{font:600 16px/1.35 var(--sans);margin:22px 0 8px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:12.5px;white-space:nowrap}
.pill.PASS{background:var(--pass-bg);color:var(--pass)}.pill.FAIL{background:var(--fail-bg);color:var(--fail)}
.pill.INCONCLUSIVE,.pill.NOT{background:var(--review-bg);color:var(--review)}
table{border-collapse:collapse;width:100%}
.ledger{background:var(--surface);border:1px solid var(--rule);border-radius:12px;overflow:hidden}
.ledger th,.ledger td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--rule);vertical-align:top}
.ledger tr:last-child td{border-bottom:0}.ledger th{font-size:12.5px;color:var(--muted);font-weight:600;background:var(--soft)}
.ledger td.kind{color:var(--muted);white-space:nowrap}
@media (max-width:640px){.ledger tr:first-child{display:none}.ledger tr{display:grid;grid-template-columns:1fr auto;
border-bottom:1px solid var(--rule)}.ledger tr:last-child{border-bottom:0}.ledger td{border-bottom:0;padding:8px 14px}
.ledger td.kind{display:none}.ledger td:last-child{grid-column:1/-1;padding-top:0;color:var(--muted)}
.wrap{padding:20px 16px 48px}.decision{padding:20px 18px}}
.change{margin-top:30px;padding-top:6px;border-top:2px solid var(--rule)}
.change>header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.change>header h2{margin:22px 0 4px}.sub{color:var(--muted);margin:0 0 8px;max-width:80ch}
.finding{background:var(--surface);border:1px solid var(--rule);border-radius:12px;margin:12px 0;padding:16px 18px}
.finding .what{font-size:16.5px;line-height:1.5;margin:6px 0 2px;max-width:78ch}
.impact{font-size:12.5px;font-weight:600;color:var(--fail)}
.impact.values,.impact.numbers{color:var(--review)}
details{margin-top:10px}summary{cursor:pointer;color:var(--accent);font-weight:600;font-size:13.5px}
summary:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.evidence{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:16px;margin-top:12px}
@media (max-width:760px){.evidence{grid-template-columns:1fr}}
.panel h4{margin:0 0 6px;font-size:12.5px;color:var(--muted);font-weight:600}
.grid{overflow-x:auto;border:1px solid var(--rule);border-radius:8px}
.grid table{font-family:var(--mono);font-size:12.5px}
.grid th,.grid td{padding:5px 9px;border-bottom:1px solid var(--rule);text-align:left;white-space:nowrap}
.grid th{background:var(--soft);font-weight:600}.grid tr:last-child td{border-bottom:0}
td.m{background:var(--mark);color:var(--mark-ink);font-weight:600}
td.d .was{color:var(--muted);text-decoration:line-through;margin-right:6px}td.d .now{font-weight:700;color:var(--fail)}
tr.only-original td{color:var(--muted);text-decoration:line-through}tr.only-fix td{color:var(--fail);font-weight:600}
.empty{color:var(--muted);font-style:italic}
.rowtag{font-family:var(--sans);font-size:11.5px;color:var(--muted)}
pre.cmd{background:var(--soft);border:1px solid var(--rule);border-radius:8px;padding:10px 12px;overflow-x:auto;margin:8px 0 0}
.copy{font:600 12.5px var(--sans);color:var(--accent);background:none;border:1px solid var(--rule);border-radius:6px;
padding:3px 10px;cursor:pointer;margin-top:8px}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--soft);gap:2px;margin:8px 0 6px}
.bar span{display:block;height:100%}.s-ok{background:var(--pass)}.s-ch{background:var(--fail)}.s-nc{background:var(--muted)}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 24px;font-size:13.5px;margin-top:10px}
.facts div{padding:6px 0;border-bottom:1px solid var(--rule)}.facts b{display:block;font-size:12px;color:var(--muted);font-weight:600}
ul.notes{margin:8px 0;padding-left:20px;color:var(--muted)}
.skipped{color:var(--muted);font-size:13.5px}
footer{margin-top:40px;color:var(--muted);font-size:12.5px}
@media print{.copy,summary{display:none}details{display:block}details>*{display:block}}
"""

JS = """
document.querySelectorAll('button.copy').forEach(function(b){b.addEventListener('click',function(){
var t=document.getElementById(b.dataset.for).innerText;
(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent='Copied';
setTimeout(function(){b.textContent='Copy commands'},1500)},function(){b.textContent='Select and copy'})})});
var all=document.getElementById('expand');if(all){all.addEventListener('click',function(){
var open=all.dataset.open!=='1';document.querySelectorAll('details.ev').forEach(function(d){d.open=open});
all.dataset.open=open?'1':'0';all.textContent=open?'Hide all evidence':'Show all evidence'})}
"""


def _grid_input(inp: dict) -> str:
    if not inp.get("header"):
        return "<p class=empty>empty: no rows</p>"
    marks = {tuple(m) for m in inp.get("marks", [])}
    head = "".join(f"<th>{E(str(h))}</th>" for h in inp["header"])
    body = []
    for ri, r in enumerate(inp["rows"]):
        cells = []
        for ci in range(len(inp["header"])):
            v = r[ci] if ci < len(r) else ""
            cls = ' class="m"' if (ri, ci) in marks else ""
            cells.append(f"<td{cls}>{E(v) if v != '' else '<span class=empty>empty</span>'}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    more = f"<p class=rowtag>and {inp['more_rows']} more rows</p>" if inp.get("more_rows") else ""
    return f"<div class=grid><table><tr>{head}</tr>{''.join(body)}</table></div>{more}"


def _grid_outputs(view: dict) -> str:
    if not view["columns"]:
        return "<p class=empty>both outputs are empty</p>"
    head = "".join(f"<th>{E(str(c))}</th>" for c in view["columns"])
    body = []
    for r in view["rows"][:20]:
        cls = {"original": ' class="only-original"', "fix": ' class="only-fix"'}.get(r["state"], "")
        cells = []
        for c in r["cells"]:
            b, a = c["before"], c["after"]
            if r["state"] == "both" and c["changed"]:
                cells.append(f"<td class=d><span class=was>{E(b) if b else 'empty'}</span>"
                             f"<span class=now>{E(a) if a else 'empty'}</span></td>")
            else:
                v = a if r["state"] == "fix" else b
                cells.append(f"<td>{E(v) if v not in (None, '') else '<span class=empty>empty</span>'}</td>")
        tag = {"original": "only in the original's output", "fix": "only in the fix's output"}.get(r["state"])
        if tag:
            cells[-1] = cells[-1][:-5] + f" <span class=rowtag>({tag})</span></td>"
        body.append(f"<tr{cls}>" + "".join(cells) + "</tr>")
    return f"<div class=grid><table><tr>{head}</tr>{''.join(body)}</table></div>"


def _finding(d: dict, ex: dict | None, repro_cmd: str | None, idx: str) -> str:
    impact = d.get("impact") or (ex or {}).get("impact")
    label = IMPACTS.get(impact or "", "Security" if impact == "security" else "Difference")
    sentence = d.get("explanation") or (ex or {}).get("sentence") or f"{d['category']} input changes the output"
    parts = [f"<article class=finding><div class='impact {E(impact or '')}'>{E(label)}</div>",
             f"<p class=what>{E(sentence).replace('`', '')}</p>"]
    ev = []
    if ex and ex.get("input"):
        inp = ex["input"]
        name = f"Input: <code>{E(inp['name'])}</code>" if inp.get("name") else "Input"
        shrunk = " (the smallest input that shows it)" if d.get("shrunk") else ""
        extra = ""
        for tname, t in (inp.get("other_tables") or {}).items():
            extra += f"<h4 style='margin-top:10px'>Also loaded: <code>{E(tname)}</code></h4>" + _grid_input(
                {"header": t["header"], "rows": t["rows"], "marks": []})
        ev.append(f"<div class=panel><h4>{name}{shrunk}</h4>{_grid_input(inp)}{extra}</div>")
    if ex and ex.get("outputs"):
        model = f" of <code>{E(ex['model'])}</code>" if ex.get("model") else ""
        ev.append(f"<div class=panel><h4>Output{model}: original, and the fix where it differs</h4>"
                  f"{_grid_outputs(ex['outputs'])}</div>")
    elif ex and ex.get("error"):
        orig = ex.get("original_output")
        shown = _grid_input(orig) if orig and orig.get("header") else "<p class=empty>empty: no rows</p>"
        ev.append(f"<div class=panel><h4>The original's output</h4>{shown}"
                  f"<h4 style='margin-top:12px'>The fix fails</h4><pre class=cmd>{E(ex['error'])}</pre></div>")
    tech = "".join(f"<li>{E(x)}</li>" for x in d.get("details", [])[:4])
    cmd = ""
    if repro_cmd:
        cmd = (f"<h4 style='margin-top:12px'>Reproduce it</h4><pre class=cmd id='cmd{idx}'>{E(repro_cmd)}</pre>"
               f"<button class=copy data-for='cmd{idx}'>Copy commands</button>")
    if ev or tech or cmd:
        parts.append(f"<details class=ev><summary>Evidence</summary><div class=evidence>{''.join(ev)}</div>"
                     f"<ul class=notes><li>Case {E(d['id'])}: <code>{E(d['category'])}</code> value "
                     f"<code>{E(repr(d['value']))}</code> in <code>{E(str(d['column']))}</code>, {E(d['status'])}</li>"
                     f"{tech}</ul>{cmd}</details>")
    parts.append("</article>")
    return "".join(parts)


def _how(proof: dict) -> str:
    beh = proof["behavior"]
    total = beh["identical"] + beh["changed"] + beh["not_comparable"]
    seg = ""
    if total:
        for cls, n in (("s-ok", beh["identical"]), ("s-ch", beh["changed"]), ("s-nc", beh["not_comparable"])):
            if n:
                seg += f"<span class={cls} style='flex:{n}' title='{n}'></span>"
    cats: dict[str, int] = {}
    for c in proof.get("cases", []):
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    inp = proof["inputs"]
    engine = inp.get("engine") or ("SQL" if "tables" in inp else None)
    frame = proof["config"].get("frame")
    what = (f"Python function {frame['function']}() on {' and '.join(dict.fromkeys(frame['libraries']))}" if frame
            else "dbt project" if inp.get("dbt") else f"SQL on {engine}" if "tables" in inp
            else f"script on sample {inp.get('sample', {}).get('name', '')}")
    sec = proof["security"]
    facts = [("Checked as", what),
             ("Generated inputs", f"{len(proof.get('cases', []))} across {len(cats)} kinds"),
             ("Security", f"{sec['fix_exploited']} of {sec['payloads']} attack payloads worked on the fix"
              if sec.get("checked") else "not checked (attack payloads off)"),
             ("Confidence", f"{proof['confidence']['score']}/100 ({proof['confidence']['level']})")]
    if inp.get("dbt"):
        facts.append(("dbt models changed", ", ".join(inp["dbt"]["changed_models"])))
        facts.append(("dbt models compared", ", ".join(inp["dbt"]["compared"])))
    if proof.get("incident"):
        facts.append(("Incident", proof["incident"]["status"]))
    kinds = ", ".join(f"{k} ({n})" for k, n in sorted(cats.items(), key=lambda x: -x[1]))
    notes = "".join(f"<li>{E(n)}</li>" for n in proof.get("notes", []) + proof.get("warnings", []))
    limits = "".join(f"<li>{E(x)}</li>" for x in proof.get("limitations", []))
    return (f"<h3>How it was checked</h3>"
            f"<div class=bar role=img aria-label='{beh['identical']} identical, {beh['changed']} changed, "
            f"{beh['not_comparable']} not comparable'>{seg}</div>"
            f"<div class=legend><span><i class=s-ok></i>{beh['identical']} gave the same output</span>"
            f"<span><i class=s-ch></i>{beh['changed']} changed</span>"
            f"<span><i class=s-nc></i>{beh['not_comparable']} not comparable (the original failed too)</span></div>"
            f"<div class=facts>{''.join(f'<div><b>{E(k)}</b>{E(str(v))}</div>' for k, v in facts)}</div>"
            f"<details><summary>Kinds of input, notes and limits</summary><p class=sub>{E(kinds)}</p>"
            f"<ul class=notes>{notes}</ul><ul class=notes>{limits}</ul>"
            f"<p class=sub>Proof ID <code>{E(proof['proof_id'][:16])}</code>, fixwitness "
            f"{E(str(proof.get('tool', {}).get('version', '')))}</p>"
            f"</details>")


def _repro_cmd(repro_dir: Path | None, cid: str) -> str | None:
    if repro_dir is None:
        return None
    readme = repro_dir / cid / "README.md"
    if not readme.is_file():
        return None
    text = readme.read_text(encoding="utf-8")
    if "```bash" not in text:
        return None
    return text.split("```bash", 1)[1].split("```", 1)[0].strip()


def _change_section(check: dict, idx: int) -> str:
    proof = check.get("proof")
    target, verdict = check["target"], check["verdict"]
    pill = f"<span class='pill {E(verdict.split()[0])}'>{E(verdict.title() if verdict == 'NOT CHECKED' else verdict)}</span>"
    head = f"<section class=change id='c{idx}'><header><h2>{E(target)}</h2>{pill}</header>"
    if proof is None:
        return head + f"<p class=sub>Not checked: {E(check.get('reason', ''))}</p></section>"
    explained = check.get("explained") or {}
    diffs = [d for d in proof["differences"] if d["kind"] != "review"]
    body = []
    beh = proof["behavior"]
    compared = beh["identical"] + beh["changed"]
    other = [r for r in proof["reasons"] if "changes output" not in r]
    if beh["changed"]:
        body.append(f"<p class=sub>{beh['changed']} of {compared} generated inputs gave a different result; "
                    f"{beh['identical']} gave the same.</p>")
    elif verdict == "PASS":
        body.append(f"<p class=sub>All {beh['identical']} generated inputs gave the same output.</p>")
    if other:
        body.append(f"<p class=sub>{E('; '.join(other)).capitalize()}.</p>")
    if diffs:
        body.append("<h3>What could go wrong</h3>")
        for j, d in enumerate(diffs[:25]):
            body.append(_finding(d, explained.get(d["id"]), _repro_cmd(check.get("repro_dir"), d["id"]), f"{idx}-{j}"))
        if len(diffs) > 25:
            body.append(f"<p class=sub>and {len(diffs) - 25} more differences in proof.json.</p>")
    body.append(_how(proof))
    return head + "".join(body) + "</section>"


def render(checks: list[dict], skipped: list[tuple[str, str]], title: str, context: str) -> str:
    """The whole page. Each check: target, kind, verdict, proof, explained (by case id), repro_dir."""
    verdicts = [c["verdict"] for c in checks]
    verdict = "FAIL" if "FAIL" in verdicts else ("PASS" if verdicts and all(v == "PASS" for v in verdicts)
                                                 else "INCONCLUSIVE")
    failed = [c for c in checks if c["verdict"] == "FAIL"]
    headline, tone = decision(verdict, 0, len(checks), len(failed))
    first = headline.split(":", 1)
    h1, why = (first[0], first[1].strip()) if len(first) == 2 else (headline, "")
    why = why[:1].upper() + why[1:]
    reasons = []
    for c in failed[:3]:
        p = c.get("proof") or {}
        d = next((x for x in p.get("differences", []) if x["kind"] != "review" and x.get("explanation")), None)
        reasons.append(f"<b>{E(c['target'])}</b>: {E((d or {}).get('explanation') or '; '.join(p.get('reasons', [])))}"
                       .replace("`", ""))
    why_html = f"<p>{E(why)}</p>" + (
        "<ul class=notes style='color:var(--ink)'>" + "".join(f"<li>{r}</li>" for r in reasons) + "</ul>" if reasons else "")
    rows = []
    for i, c in enumerate(checks):
        p = c.get("proof") or {}
        d = next((x for x in p.get("differences", []) if x["kind"] != "review" and x.get("explanation")), None)
        line = (d or {}).get("explanation") or (c.get("reason") if c.get("reason") not in (None, "-") else None) or (
            f"{p.get('behavior', {}).get('identical', 0)} inputs gave the same output" if c["verdict"] == "PASS" else "")
        rows.append(f"<tr><td><a href='#c{i}'>{E(c['target'])}</a></td><td class=kind>{E(c['kind'])}</td>"
                    f"<td><span class='pill {E(c['verdict'].split()[0])}'>{E(c['verdict'])}</span></td>"
                    f"<td>{E(str(line)).replace('`', '')}</td></tr>")
    ledger = ("<table class=ledger><tr><th>Changed</th><th>Checked as</th><th>Result</th><th>What it found</th></tr>"
              + "".join(rows) + "</table>")
    skipped_html = ("<p class=skipped>Not checked: " + "; ".join(f"<code>{E(p)}</code> ({E(w)})" for p, w in skipped)
                    + "</p>") if skipped else ""
    sections = "".join(_change_section(c, i) for i, c in enumerate(checks))
    any_evidence = any((c.get("proof") or {}).get("differences") for c in checks)
    expand = "<p><button class=copy id=expand>Show all evidence</button></p>" if any_evidence else ""
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'><title>{E(title)}</title>"
            f"<style>{CSS}</style></head><body><div class=wrap>"
            f"<div class=top><span><b>fixwitness</b> report</span><span>{E(context)}</span></div>"
            f"<div class='decision tone-{tone}'><h1>{E(h1)}</h1>{why_html}</div>"
            f"<h2>Changes</h2>{ledger}{skipped_html}{expand}{sections}"
            f"<footer>Generated inputs are your sample data with one thing changed at a time; a difference means "
            f"the change behaves differently on data your systems can produce. Each proof can be re-checked with "
            f"<code>fixwitness replay</code>.</footer></div><script>{JS}</script></body></html>")


def check_entry(proof: dict, out_dir: Path | None, target: str | None = None, kind: str | None = None) -> dict:
    from fixwitness.core import REPRO
    info = REPRO.get(proof["proof_id"]) or {}
    return {"target": target or proof.get("inputs", {}).get("target") or proof["inputs"].get("after", {}).get("name")
            or "change", "kind": kind or _kind(proof), "verdict": proof["verdict"], "proof": proof,
            "explained": info.get("explained") or {}, "repro_dir": (out_dir / "repro") if out_dir else None}


def _kind(proof: dict) -> str:
    inp = proof["inputs"]
    if proof["config"].get("frame"):
        return "dataframe"
    if inp.get("dbt"):
        return "dbt"
    if "tables" in inp:
        return "sql"
    return "script"


def context_line(proof: dict) -> str:
    inp = proof["inputs"]
    when = proof.get("created_utc", "").replace("T", " ").replace("Z", " UTC")
    if inp.get("mode") == "git":
        return f"Original: commit {inp.get('base_commit', '')[:12]}. Fix: your working tree. Checked {when}"
    return f"Original and fix compared {when}"


def write_single(proof: dict, out_dir: Path) -> Path:
    page = render([check_entry(proof, out_dir)], [], "fixwitness report", context_line(proof))
    path = out_dir / "report.html"
    path.write_text(page, encoding="utf-8")
    return path


def dumps_summary(result: dict) -> str:
    return json.dumps(result, indent=2)
