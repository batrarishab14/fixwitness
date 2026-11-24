"""fixwitness ui: a local web app for people who would rather not live in a terminal.

    fixwitness ui            # opens http://127.0.0.1:<port>/?t=<token> in your browser

It shows what changed against a base branch and how each file will be checked, runs the check
with live progress, shows the report, and lets you mark a difference as intended (written to
fixwitness.toml as [[accept]], so the next run reports it as reviewed instead of failed).

Only the Python standard library. The server listens on 127.0.0.1 only and every request must
carry a random token, so other web pages can't drive it.
"""

from __future__ import annotations

import dataclasses
import html
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

E = html.escape


class State:
    def __init__(self, root: Path):
        self.root = root
        self.token = secrets.token_urlsafe(18)
        self.lock = threading.Lock()
        self.status: dict = {"running": False}
        self.runs: list[dict] = []  # newest last: {id, started, base, verdict, checks, skipped, out}

    def config(self, base: str, attacks: bool, max_cases: int):
        from fixwitness.config import load_config
        toml = self.root / "fixwitness.toml"
        overrides = {"base": base or "HEAD", "attacks": attacks, "max_cases": max_cases}
        if toml.is_file():
            import tomllib
            with toml.open("rb") as fh:
                raw = tomllib.load(fh)
            overrides["accept"] = raw.get("accept")
        return load_config(None, overrides)

    def plan(self, base: str) -> dict:
        from fixwitness.changes import plan_items
        cfg = self.config(base, True, 300)
        items, skipped = plan_items(cfg)
        return {"root": str(self.root), "items": [{"target": i.target, "kind": i.kind} for i in items],
                "skipped": [{"path": p, "why": w} for p, w in skipped]}

    def start(self, base: str, attacks: bool, max_cases: int) -> str:
        with self.lock:
            if self.status.get("running"):
                raise RuntimeError("a check is already running")
            run_id = time.strftime("%Y%m%d-%H%M%S")
            self.status = {"running": True, "run": run_id, "index": 0, "total": 0, "current": "planning",
                           "done": [], "error": None, "started": time.time()}
        threading.Thread(target=self._run, args=(run_id, base, attacks, max_cases), daemon=True).start()
        return run_id

    def _run(self, run_id: str, base: str, attacks: bool, max_cases: int) -> None:
        from fixwitness.changes import plan_items, run_items
        from fixwitness.core import REPRO
        out = self.root / ".fixwitness" / "ui" / run_id
        try:
            cfg = self.config(base, attacks, max_cases)
            items, skipped = plan_items(cfg)
            self.status.update(total=len(items))
            checks = []
            for i, item in enumerate(items):
                self.status.update(index=i + 1, current=item.target)
                result = run_items(cfg, [item], out)
                for r in result["checks"]:
                    proof = r.get("_proof")
                    info = REPRO.get(proof["proof_id"], {}) if proof else {}
                    checks.append({"target": r["target"], "kind": r["kind"], "verdict": r["verdict"], "proof": proof,
                                   "reason": r.get("reason"), "explained": info.get("explained") or {},
                                   "repro_dir": Path(r["proof"]).parent / "repro" if r.get("proof") else None})
                    self.status["done"].append({"target": r["target"], "verdict": r["verdict"]})
            verdicts = [c["verdict"] for c in checks]
            verdict = "FAIL" if "FAIL" in verdicts else ("PASS" if verdicts and all(v == "PASS" for v in verdicts)
                                                         else "INCONCLUSIVE")
            run = {"id": run_id, "started": self.status["started"], "base": base, "verdict": verdict,
                   "checks": checks, "skipped": skipped, "out": out}
            out.mkdir(parents=True, exist_ok=True)
            (out / "report.html").write_text(self.report(run, interactive=False), encoding="utf-8")
            with self.lock:
                self.runs.append(run)
                self.status.update(running=False, current=None, verdict=verdict)
        except Exception as exc:  # shown in the app, not swallowed
            with self.lock:
                self.status.update(running=False, error=f"{type(exc).__name__}: {exc}")

    def report(self, run: dict, interactive: bool) -> str:
        from fixwitness.htmlreport import render
        context = f"Original: {run['base']}. Fix: your working tree. Checked {time.strftime('%Y-%m-%d %H:%M', time.localtime(run['started']))}"
        page = render(run["checks"], run["skipped"], "fixwitness report", context, interactive=interactive)
        if interactive:
            page = page.replace("<head>", f"<head><meta name=fw-token content='{self.token}'>", 1)
        return page

    def accept(self, body: dict) -> dict:
        from fixwitness.config import append_accept
        category = str(body.get("category") or "")
        if not category:
            raise ValueError("category is required")
        return append_accept(self.root / "fixwitness.toml", body.get("target") or None, category,
                             body.get("column") or None, body.get("note") or None)


def _page(state: State) -> str:
    return (APP.replace("__TOKEN__", state.token).replace("__ROOT__", E(str(state.root)))
            .replace("__CSS__", _css()))


def _css() -> str:
    from fixwitness.htmlreport import CSS
    return CSS


class Handler(BaseHTTPRequestHandler):
    state: State = None  # set by serve()

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _allowed(self, query: dict) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        token = self.headers.get("X-Fixwitness-Token") or (query.get("t") or [""])[0]
        return host in ("127.0.0.1", "localhost") and secrets.compare_digest(token, self.state.token)

    def _send(self, code: int, body: str | bytes, ctype: str = "application/json") -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, default=str))

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if not self._allowed(q):
            return self._send(403, "open the address fixwitness ui printed (it carries a token)", "text/plain")
        s = self.state
        if url.path == "/":
            return self._send(200, _page(s), "text/html")
        if url.path == "/api/plan":
            try:
                return self._json(200, s.plan((q.get("base") or ["HEAD"])[0]))
            except Exception as exc:
                return self._json(400, {"error": str(exc).splitlines()[0]})
        if url.path == "/api/status":
            st = dict(s.status)
            st["runs"] = [{"id": r["id"], "verdict": r["verdict"], "base": r["base"],
                           "checks": len(r["checks"]), "started": r["started"]} for r in s.runs[::-1]]
            return self._json(200, st)
        if url.path == "/report":
            run_id = (q.get("run") or [""])[0]
            run = next((r for r in s.runs if r["id"] == run_id), None)
            if run is None:
                return self._send(404, "no such run", "text/plain")
            return self._send(200, s.report(run, interactive=True), "text/html")
        return self._send(404, "not found", "text/plain")

    def do_POST(self):
        url = urlparse(self.path)
        if not self._allowed(parse_qs(url.query)):
            return self._send(403, "missing token", "text/plain")
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 100_000)
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json(400, {"error": "the request body must be JSON"})
        try:
            if url.path == "/api/run":
                run_id = self.state.start(str(body.get("base") or "HEAD"), bool(body.get("attacks", False)),
                                          max(10, min(5000, int(body.get("max_cases") or 300))))
                return self._json(200, {"run": run_id})
            if url.path == "/api/accept":
                return self._json(200, {"accepted": self.state.accept(body)})
        except (RuntimeError, ValueError) as exc:
            return self._json(409, {"error": str(exc)})
        return self._send(404, "not found", "text/plain")


def serve(port: int = 0, open_browser: bool = True, root: Path | None = None) -> int:
    from fixwitness.plan import repo_root
    try:
        root = repo_root(root or Path.cwd())
    except Exception:
        root = root or Path.cwd()
    state = State(root)
    handler = type("BoundHandler", (Handler,), {"state": state})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/?t={state.token}"
    print(f"fixwitness ui: {url}\n(press Ctrl+C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


APP = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'><title>fixwitness</title>
<style>__CSS__
.app-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline}
.app-head h1{font:600 28px/1.2 var(--serif);margin:0}
.runbar{display:flex;gap:12px;flex-wrap:wrap;align-items:end;background:var(--surface);border:1px solid var(--rule);
border-radius:14px;padding:18px 20px;margin:18px 0}
label{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--muted);font-weight:600}
input[type=text],input[type=number]{font:15px var(--sans);padding:8px 10px;border:1px solid var(--rule);border-radius:8px;
background:var(--bg);color:var(--ink);min-width:0}
input[type=text]{width:220px}input[type=number]{width:110px}
.check{flex-direction:row;align-items:center;gap:8px;font-weight:500;color:var(--ink);font-size:14px;padding-bottom:9px}
.primary{font:600 15px var(--sans);background:var(--accent);color:#fff;border:0;border-radius:9px;padding:10px 18px;cursor:pointer}
.primary:disabled{opacity:.5;cursor:default}
.progress{height:8px;border-radius:4px;background:var(--soft);overflow:hidden;margin:6px 0}
.progress i{display:block;height:100%;background:var(--accent);width:0;transition:width .4s}
iframe{width:100%;border:1px solid var(--rule);border-radius:14px;background:var(--bg);min-height:80vh}
.status{color:var(--muted);font-size:14px;min-height:1.5em}.err{color:var(--fail)}
.runs a{margin-right:14px}
</style></head><body><div class=wrap>
<div class=app-head><h1>fixwitness</h1><span class=sub>__ROOT__</span></div>
<form class=runbar id=form>
<label>Compare your working tree with<input type=text id=base value=HEAD autocomplete=off></label>
<label>Inputs per change<input type=number id=cases value=300 min=10 max=5000></label>
<label class=check><input type=checkbox id=attacks> Try attack payloads (security fixes)</label>
<button class=primary id=go type=submit>Check my changes</button>
</form>
<h2>What will be checked</h2><div id=plan class=status>Looking for changes</div>
<div id=progress hidden><h2>Checking</h2><div class=progress><i id=bar></i></div><div id=now class=status></div></div>
<div id=result hidden><h2>Report</h2><iframe id=frame title="fixwitness report"></iframe></div>
<div id=history class=runs></div>
</div><script>
var T='__TOKEN__';function api(p,o){o=o||{};o.headers=Object.assign({'X-Fixwitness-Token':T,'Content-Type':'application/json'},o.headers||{});
return fetch(p,o).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||r.status);return j})})}
function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function plan(){var b=document.getElementById('base').value||'HEAD';var el=document.getElementById('plan');
el.textContent='Looking for changes against '+b;
api('/api/plan?base='+encodeURIComponent(b)).then(function(p){
if(!p.items.length&&!p.skipped.length){el.innerHTML='No changes against '+esc(b)+'. Edit a file, or compare with another branch.';return}
var rows=p.items.map(function(i){return '<tr><td>'+esc(i.target)+'</td><td class=kind>'+esc(i.kind)+'</td><td></td></tr>'})
.concat(p.skipped.map(function(s){return '<tr><td>'+esc(s.path)+'</td><td class=kind>-</td><td class=sub>not checked: '+esc(s.why)+'</td></tr>'}));
el.className='';el.innerHTML='<table class=ledger><tr><th>Changed</th><th>Checked as</th><th></th></tr>'+rows.join('')+'</table>'
}).catch(function(e){el.className='status err';el.textContent=e.message})}
var timer=null;
function poll(){api('/api/status').then(function(s){
var pr=document.getElementById('progress'),now=document.getElementById('now');
if(s.running){pr.hidden=false;document.getElementById('bar').style.width=(s.total?Math.round(100*(s.index-1)/s.total):5)+'%';
now.textContent=s.total?('Checking '+s.index+' of '+s.total+': '+s.current):'Finding what changed';return}
clearInterval(timer);timer=null;document.getElementById('go').disabled=false;pr.hidden=true;
if(s.error){now.className='status err';pr.hidden=false;now.textContent=s.error;return}
if(s.runs&&s.runs.length){show(s.runs[0].id);history(s.runs)}})}
function show(id){document.getElementById('result').hidden=false;document.getElementById('frame').src='/report?run='+encodeURIComponent(id)+'&t='+T}
function history(runs){document.getElementById('history').innerHTML=runs.length>1?'<h2>Earlier runs</h2>'+runs.slice(1).map(function(r){
return '<a href="#" data-run="'+esc(r.id)+'">'+esc(r.id)+' '+esc(r.verdict)+'</a>'}).join(''):'';
document.querySelectorAll('#history a').forEach(function(a){a.onclick=function(e){e.preventDefault();show(a.dataset.run)}})}
document.getElementById('form').addEventListener('submit',function(e){e.preventDefault();
document.getElementById('go').disabled=true;
api('/api/run',{method:'POST',body:JSON.stringify({base:document.getElementById('base').value,
max_cases:+document.getElementById('cases').value,attacks:document.getElementById('attacks').checked})})
.then(function(){if(!timer)timer=setInterval(poll,800);poll()}).catch(function(err){document.getElementById('go').disabled=false;alert(err.message)})});
document.getElementById('base').addEventListener('change',plan);
plan();api('/api/status').then(function(s){if(s.running){timer=setInterval(poll,800)}else if(s.runs&&s.runs.length){show(s.runs[0].id);history(s.runs)}});
</script></body></html>"""
