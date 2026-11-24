"""Model Context Protocol server (stdio) so coding agents can check their own fixes.

Zero dependencies: newline-delimited JSON-RPC 2.0 on stdin/stdout, as the MCP stdio
transport specifies. Diagnostics go to stderr only.

Tools:
  prove_fix     compare the original with the fix and return a verdict, a confidence score and
                the path of a replayable proof record. Simplest call: {"path": "etl/clean.py"}.
  replay_proof  re-run a saved proof and report whether it reproduces
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from fixwitness import __version__
from fixwitness.cases import CATEGORY_DESCRIPTIONS, SampleError
from fixwitness.formats import JSON_CATEGORY_DESCRIPTIONS
from fixwitness.config import ConfigError, load_config
from fixwitness.core import dry_run, replay, run_check
from fixwitness.report import markdown, plan_text, write_outputs
from fixwitness.runner import RunConfigError

SUPPORTED_PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "After you edit code to fix a security finding or to repair a failing pipeline, and before you propose, "
    "commit or deploy the change, call "
    "prove_fix with the path of the file you changed (the original is taken from git HEAD and the fix from "
    "the working tree). If the fix spans several files, pass 'command' instead (the entry point, run from the "
    "repository root). For a repair, pass incident_path (the input that broke the pipeline) and attacks=false. "
    "Only propose the fix if the verdict is PASS; if it is FAIL, read the listed differences, "
    "adjust the fix and call prove_fix again. Put the summary and proof ID in the pull request description."
)

_REVIEWABLE = sorted((set(CATEGORY_DESCRIPTIONS) | set(JSON_CATEGORY_DESCRIPTIONS)) - {"attack"})

TOOLS = [
    {
        "name": "prove_fix",
        "title": "Prove a fix is safe",
        "description": (
            "Compare the original code with the fixed code on generated inputs derived from a sample CSV. "
            "PASS means attack payloads (command/code injection, path traversal, template injection) no longer "
            "work on the fix AND every valid input gives the same output as before. Returns a 0-100 confidence "
            "score and the path of a JSON proof record. Simplest call: {\"path\": \"etl/clean.py\"} - the "
            "original comes from git HEAD, the run command and sample file are detected. Code is executed on "
            "this machine. SQL queries and dbt models (.sql) are checked too: give the tables the query reads, "
            "e.g. {\"path\": \"models/revenue.sql\", \"tables\": {\"orders\": \"data/orders.csv\"}}; "
            "both versions run on the same generated tables (DuckDB if installed, else SQLite). A folder of "
            "models is run as a pipeline in dependency order, and SQL written for a warehouse is translated "
            "with sqlglot (dialect: snowflake, bigquery, ...). Python DataFrame code (pandas, polars, PySpark) is "
            "checked by calling a function with generated tables: {\"path\": \"etl/revenue.py\", "
            "\"function\": \"revenue\", \"tables\": {\"orders\": \"data/orders.csv\"}}."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File you changed (git mode). Original = this file at 'base'."},
                "base": {"type": "string", "description": "Git revision with the original. Default HEAD."},
                "command": {"type": "string", "description": "Entry command for fixes spread over several files, "
                            "run from the repo root, e.g. 'python3 etl/run.py {input} {output}'."},
                "before_path": {"type": "string", "description": "Original file, if not using git."},
                "after_path": {"type": "string", "description": "Fixed file, if not using git."},
                "sample_path": {"type": "string", "description": "Sample CSV with a header row. Found automatically "
                                "when there is exactly one CSV next to the script."},
                "incident_path": {"type": "string", "description": "Self-healing repairs: the input that broke the "
                                  "original. PASS requires the fix to process it."},
                "incident_expected_path": {"type": "string", "description": "Optional: the correct output for "
                                           "the incident input, if known."},
                "tables": {"type": "object", "additionalProperties": {"type": "string"},
                           "description": "SQL/dbt: table name -> sample CSV for every table the query reads."},
                "incident_tables": {"type": "object", "additionalProperties": {"type": "string"},
                                    "description": "SQL/dbt: table name -> CSV with that table's contents when the "
                                    "original broke."},
                "engine": {"type": "string", "enum": ["auto", "duckdb", "sqlite"],
                           "description": "SQL/dbt engine (default: DuckDB if installed, else SQLite)."},
                "sql_ordered": {"type": "boolean", "description": "SQL/dbt: compare result rows in order."},
                "dialect": {"type": "string",
                            "description": "SQL/dbt: the warehouse the SQL is written for (snowflake, bigquery, "
                                           "postgres, tsql, ...). Needs sqlglot."},
                "function": {"type": "string",
                             "description": "Python DataFrame code: the function to call with the tables "
                                            "(name the tables after its parameters)."},
                "library": {"type": "string", "enum": ["auto", "pandas", "polars", "pyspark"],
                            "description": "DataFrame library (default: from the script's imports)."},
                "sql_outputs": {"type": "array", "items": {"type": "string"},
                                "description": "SQL/dbt folder of models: the models to compare "
                                               "(default: the final ones; [\"all\"] for every model)."},
                "attacks": {"type": "boolean", "description": "Run attack payloads (default true). Set false for "
                            "pipeline repairs and refactors that are not security fixes."},
                "run_command": {"type": "string", "description": "How to run one script, e.g. "
                                "'python3 {script} {input} {output}'. Detected when omitted."},
                "columns": {"type": "array", "items": {"type": "string"},
                            "description": "Columns to probe (default all). Prefer the columns the finding is about."},
                "review_categories": {"type": "array", "items": {"type": "string", "enum": _REVIEWABLE},
                                      "description": "Categories where differences are expected; reported, not failed."},
                "ignore_columns": {"type": "array", "items": {"type": "string"},
                                   "description": "Output columns to leave out of the comparison."},
                "ignore_patterns": {"type": "array", "items": {"type": "string"},
                                    "description": "Regexes masked out of compared values (e.g. timestamps)."},
                "tolerance": {"type": "number", "minimum": 0, "description": "Relative numeric tolerance."},
                "unordered": {"type": "boolean", "description": "Ignore row order."},
                "output": {"type": "string", "enum": ["csv", "json", "text"]},
                "manifest": {"type": "string", "description": "dbt: the fix's target/manifest.json (from dbt compile)."},
                "base_manifest": {"type": "string", "description": "dbt: the original's manifest.json."},
                "max_cases": {"type": "integer", "minimum": 10, "maximum": 5000},
                "seed": {"type": "integer"},
                "dry_run": {"type": "boolean", "description": "Only show what would be compared."},
                "proof_dir": {"type": "string", "description": "Where to write proof.json and report.md "
                              "(default: .fixwitness in the current folder)."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "prove_change",
        "title": "Check everything a change touched",
        "description": (
            "Check every file changed in the working tree against git 'base' (default HEAD), with no other "
            "setup: dbt projects (compiled by dbt when it is installed), SQL files (tables found by name among "
            "the data files), pandas/polars/PySpark functions that changed (tables matched to their parameter "
            "names), and scripts that read CSV, JSON, JSON Lines or Parquet. Returns one verdict, a row per "
            "check, and the files not checked with the reason. Call it before you open a pull request."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "description": "Git revision with the original. Default HEAD."},
                "path": {"type": "string", "description": "Only changes under this folder or file."},
                "attacks": {"type": "boolean", "description": "Run attack payloads on scripts (default true)."},
                "engine": {"type": "string", "enum": ["auto", "duckdb", "sqlite"]},
                "dialect": {"type": "string", "description": "SQL written for this warehouse (needs sqlglot)."},
                "max_cases": {"type": "integer", "minimum": 10, "maximum": 5000},
                "proof_dir": {"type": "string", "description": "Where to write the reports (default .fixwitness)."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "replay_proof",
        "title": "Replay a saved proof",
        "description": "Re-run a proof.json from its recorded inputs and settings, check that the input files are "
                       "unchanged (SHA-256) and report whether the same evidence is produced.",
        "inputSchema": {
            "type": "object",
            "properties": {"proof_path": {"type": "string", "description": "Path to a fixwitness proof.json."}},
            "required": ["proof_path"],
            "additionalProperties": False,
        },
    },
]


def _text_result(text: str, structured: dict | None = None, is_error: bool = False) -> dict:
    result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def _prove_fix(args: dict) -> dict:
    overrides = {
        "path": args.get("path"), "base": args.get("base"), "command": args.get("command"),
        "before": args.get("before_path"), "after": args.get("after_path"),
        "sample": args.get("sample_path"), "run": args.get("run_command"),
        "incident": args.get("incident_path"), "attacks": args.get("attacks"),
        "tables": args.get("tables"), "incident_tables": args.get("incident_tables"),
        "engine": args.get("engine"), "sql_ordered": args.get("sql_ordered"),
        "dialect": args.get("dialect"), "sql_outputs": args.get("sql_outputs"),
        "function": args.get("function"), "library": args.get("library"),
        "manifest": args.get("manifest"), "base_manifest": args.get("base_manifest"),
        "incident_expected": args.get("incident_expected_path"),
        "columns": args.get("columns"), "review": args.get("review_categories"),
        "ignore_columns": args.get("ignore_columns"), "ignore_patterns": args.get("ignore_patterns"),
        "tolerance": args.get("tolerance"), "unordered": args.get("unordered"),
        "output": args.get("output"), "max_cases": args.get("max_cases"), "seed": args.get("seed"),
        "allow_any_command": False,  # MCP never runs programs outside the allow-list
    }
    cfg = load_config(None, overrides)
    if args.get("dry_run"):
        summary = dry_run(cfg)
        return _text_result(plan_text(summary), summary)
    proof = run_check(cfg)
    out_dir = Path(args["proof_dir"]) if args.get("proof_dir") else Path.cwd() / ".fixwitness"
    proof_path = write_outputs(proof, out_dir)
    structured = {
        "verdict": proof["verdict"],
        "confidence": proof["confidence"]["score"],
        "confidence_level": proof["confidence"]["level"],
        "hole_closed": proof["security"]["hole_closed"] if proof["security"]["checked"] else None,
        "incident": proof.get("incident"),
        "finding_reproduced": proof["security"]["finding_reproduced"],
        "valid_inputs_identical": proof["behavior"]["identical"],
        "valid_inputs_changed": proof["behavior"]["changed"],
        "reasons": proof["reasons"],
        "differences": [
            {"explanation": d.get("explanation"), "impact": d.get("impact"),
             "category": d["category"], "column": d["column"], "value": d["value"], "status": d["status"],
             "details": d["details"][:3]}
            for d in proof["differences"] if d["kind"] != "review"
        ][:10],
        "proof_id": proof["proof_id"],
        "proof_path": str(proof_path),
    }
    return _text_result(markdown(proof, str(proof_path)), structured)


def _prove_change(args: dict) -> dict:
    from fixwitness.changes import plan_items, run_items, summary_markdown
    cfg = load_config(None, {"base": args.get("base"), "path": args.get("path"), "attacks": args.get("attacks"),
                             "engine": args.get("engine"), "dialect": args.get("dialect"),
                             "max_cases": args.get("max_cases"), "allow_any_command": False})
    items, skipped = plan_items(cfg)
    out_dir = Path(args["proof_dir"]) if args.get("proof_dir") else Path.cwd() / ".fixwitness"
    result = run_items(cfg, items, out_dir)
    structured = {"verdict": result["verdict"],
                  "checks": [{k: v for k, v in r.items() if not k.startswith("_")} for r in result["checks"]],
                  "not_checked": [{"path": p, "why": w} for p, w in skipped]}
    return _text_result(summary_markdown(result, skipped), structured)


def _replay_proof(args: dict) -> dict:
    proof = json.loads(Path(args["proof_path"]).read_text(encoding="utf-8"))
    result = replay(proof, allow_any_command=False)
    if result["reproduced"]:
        text = f"Replay reproduced proof {result['original_proof_id'][:16]} (verdict {result['verdict']})."
    else:
        text = "Replay did NOT reproduce the proof:\n" + "\n".join(f"- {p}" for p in result["problems"])
    return _text_result(text, result)


HANDLERS = {"prove_fix": _prove_fix, "prove_change": _prove_change, "replay_proof": _replay_proof}


def handle(message: dict) -> dict | None:
    """Handle one JSON-RPC message. Returns the response, or None for notifications."""
    method = message.get("method")
    msg_id = message.get("id")
    if "id" not in message:
        return None

    def ok(result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def err(code: int, text: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": text}}

    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return ok({
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "fixwitness", "title": "fixwitness", "version": __version__},
            "instructions": INSTRUCTIONS,
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        handler = HANDLERS.get(params.get("name"))
        if handler is None:
            return err(-32602, f"unknown tool: {params.get('name')}")
        try:
            return ok(handler(params.get("arguments") or {}))
        except (ConfigError, RunConfigError, SampleError, ValueError, KeyError, OSError, TypeError) as exc:
            return ok(_text_result(f"fixwitness could not run: {exc}", is_error=True))
        except Exception as exc:  # report, don't crash the server
            traceback.print_exc(file=sys.stderr)
            return ok(_text_result(f"fixwitness internal error: {exc}", is_error=True))
    return err(-32601, f"method not found: {method}")


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"parse error: {exc}"}}
        else:
            if isinstance(message, dict):
                response = handle(message)
            else:
                response = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32600, "message": "expected a single JSON-RPC object"}}
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
