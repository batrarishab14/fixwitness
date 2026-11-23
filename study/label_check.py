"""Labelling aid for the assistant study: look for inputs the original job handles whose output a fix changes.

This is separate from fixwitness. It runs the original and each agent fix in-process on many
hand-written and random inputs for the case's changed column (plus header and delimiter variants
for I05-I07), and reports every input where the original succeeds but the fix fails or writes
different bytes. A label of "wrong" in study/labels.csv must cite one such input, or the incident
input giving the wrong output.

    python3 study/label_check.py            # all agents
    python3 study/label_check.py claude-r1  # one agent
"""

from __future__ import annotations

import contextlib
import io
import itertools
import os
import random
import runpy
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmark" / "cases"
AGENTS = ROOT / "benchmark" / "agents"

NUMBERS = ["12.50", "-42.75", "0", "-0", "-0.0", "1e3", "1E-2", "1_000", "+5", " 7.5 ", " 7", "007",
           ".5", "5.", "inf", "-inf", "nan", "0.125", "2.675", "1000000", "-0.001", "3", "-1", "1,250.00",
           "(125.00)", "(5)", "125,50", "12%", "-12%", "0.12", "N/A", "n/a", "NA", "", " ", "abc",
           "1,2", "1,25", "1.250,00", "(1,250.00)", "12.5%", " 12% ", "12 %", "%", "()", "(-5)", "-(5)",
           "１２", "٣", "1__0", "0x10", "1.2.3", "--5", "5-", "1 000", "12,", ",5", "1e", "e3"]
DATES = ["2026-01-15", "2026-1-5", "2026-01-5", " 2026-01-15", "2026-01-15 ", "2026/11/12", "2026/1/5",
         "2026-13-01", "2026-02-30", "26-01-15", "2026-01-15T00:00", "20260115", "2026.01.15", "",
         "0001-01-01", "9999-12-31", "2026-W01", "2026-01-15 ", "２０２６-01-15"]
ALPHABET = "0123456789,.-+()% e_ N/A"


def rand_values(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    return ["".join(rng.choice(ALPHABET) for _ in range(rng.randint(1, 7))) for _ in range(n)]


def run(script: Path, data: bytes) -> tuple[bool, bytes]:
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "in.csv", Path(d) / "out.csv"
        src.write_bytes(data)
        argv, cwd = sys.argv, os.getcwd()
        sys.argv = [str(script), str(src), str(dst)]
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                runpy.run_path(str(script), run_name="__main__")
            return True, dst.read_bytes() if dst.exists() else b""
        except BaseException:  # noqa: BLE001 - any failure of the job counts as "fails"
            return False, b""
        finally:
            sys.argv = argv
            os.chdir(cwd)


def csv_line(values: list[str], sep: str = ",") -> str:
    out = []
    for v in values:
        out.append('"' + v.replace('"', '""') + '"' if any(c in v for c in (sep, '"', "\n", ",", ";")) else v)
    return sep.join(out)


def value_inputs(case: str) -> list[bytes]:
    header = (CASES / case / "sample.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    col = {"I01": "amount", "I02": "amount", "I03": "day", "I04": "qty", "I08": "amount", "I09": "rate"}[case[:3]]
    pool = (DATES if col == "day" else NUMBERS) + rand_values(400, zlib.crc32(case.encode()))
    base = (CASES / case / "sample.csv").read_text(encoding="utf-8").splitlines()[1].split(",")
    inputs = []
    for v in pool:
        row = list(base)
        row[header.index(col)] = v
        inputs.append((csv_line(header) + "\n" + csv_line(row) + "\n").encode("utf-8"))
    return inputs


def header_inputs(case: str) -> list[bytes]:
    rows = []
    if case.startswith("I05"):
        heads = [["payment_id", "customer", "amount"], ["payment_id", "customer", "amount", "amount_usd"],
                 ["payment_id", "customer", "amount_usd", "amount"], ["payment_id", "customer", "currency", "amount"],
                 ["amount", "payment_id", "customer"], ["payment_id", "customer", "amount", "note"]]
        for h in heads:
            vals = {"payment_id": "P-1", "customer": "Acme", "amount": "12.50", "amount_usd": "13.75",
                    "currency": "EUR", "note": "x"}
            rows.append((csv_line(h) + "\n" + csv_line([vals[c] for c in h]) + "\n").encode())
    if case.startswith("I06"):
        for pre, enc in itertools.product(["", "﻿"], ["utf-8"]):
            for cust in ["Acme", "Café Noir", "﻿Acme", "Ａｃｍｅ"]:
                rows.append((pre + "payment_id,customer,amount\nP-1," + cust + ",12.50\n").encode(enc))
        rows.append(b"payment_id,customer,amount\r\nP-1,Acme,12.50\r\n")
    if case.startswith("I07"):
        heads = ["payment_id,customer,amount", "payment_id,customer,amount,note", "payment_id,customer,amount,a;b",
                 "payment_id,customer,amount,a;b;c", "payment_id,customer,amount,a;b;c;d",
                 'payment_id,customer,amount,"x;y;z;w"', "payment_id,customer,amount,;;;;"]
        bodies = ["P-1,Acme,12.50", "P-1,Acme;Ltd,12.50", 'P-1,"Acme, Ltd",12.50', 'P-1,"Acme; Ltd",12.50',
                  "P-1,A;B;C;D;E,12.50", 'P-1,"a;b";c,12.50', 'P-1,Acme; "Ltd"; UK,12.50',
                  "P-1,x;'y';z,12.50", 'P-1,"Acme ""Ltd""; UK",12.50']
        for h in heads:
            extra = len(next(iter([h.split(",")]))) - 3
            for b in bodies:
                rows.append((h + "\n" + b + ",x" * extra + "\n").encode())
                rows.append((h + "\n" + "\n".join([b + ",x" * extra] * 5) + "\n").encode())
        rows.append(b"payment_id,customer,amount\n")
        # added after the independent review (2026-11-20): text values mixing ';' and quotes, and a
        # header record that spans two physical lines
        rows.append(b'payment_id,customer,amount,note\nP-1,Acme,12.50,"call back; ""urgent"""\n')
        rows.append(b'payment_id,customer,amount,note\nP-1,Acme,12.50,call back; "urgent"\n')
        rows.append(b'"a;\nb",payment_id,customer,amount\nz,P-1,Acme,12.50\n')
        rows.append(b'payment_id,customer,"amount"\nP-1,"Acme;\nLtd",12.50\n')
    return rows


def main(only: str | None) -> int:
    agents = sorted(p for p in AGENTS.iterdir() if p.is_dir() and (only is None or p.name == only))
    if only == "references":  # the benchmark's own reference repairs, held to the same rule
        agents = [CASES / c / "fixes" for c in sorted(p.name for p in CASES.iterdir() if p.name.startswith("I"))]
    for case_dir in sorted(p for p in CASES.iterdir() if p.name.startswith("I")):
        case = case_dir.name
        inputs = header_inputs(case) if case[:3] in ("I05", "I06", "I07") else value_inputs(case)
        original = case_dir / "original.py"
        base = [run(original, x) for x in inputs]
        handled = sum(ok for ok, _ in base)
        expected = (case_dir / "expected.csv").read_bytes()
        incident = (case_dir / "incident.csv").read_bytes()
        for agent in agents:
            fix = agent / case / "fix.py" if only != "references" else agent / "reference.py"
            if only == "references" and agent.parent.name != case:
                continue
            if not fix.exists():
                continue
            ok_i, out_i = run(fix, incident)
            diffs = []
            for x, (ok, out) in zip(inputs, base):
                if not ok:
                    continue
                ok2, out2 = run(fix, x)
                if not ok2 or out2 != out:
                    diffs.append((x, out, out2 if ok2 else b"<fails>"))
            status = "incident OK" if ok_i and out_i == expected else "INCIDENT WRONG"
            print(f"{case:26} {agent.name:12} {status:14} changed {len(diffs)} of {handled} handled inputs")
            for x, a, b in diffs[:3]:
                print(f"    input   {x!r}\n    original {a!r}\n    fix      {b!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
