import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fixwitness.cases import CANARY_PREFIX, generate_cases  # noqa: E402
from fixwitness.compare import CompareOptions, compare, unstable_columns  # noqa: E402
from fixwitness.config import ConfigError, load_config  # noqa: E402
from fixwitness.core import dry_run, replay, run_check  # noqa: E402
from fixwitness.plan import PlanError  # noqa: E402
from fixwitness.runner import Invocation, RunConfigError, Side, build_command, no_network_available, run_side  # noqa: E402
from fixwitness.score import confidence  # noqa: E402

EXAMPLES = ROOT / "src" / "fixwitness" / "examples"
SAMPLE = "id,name,amount\n1,alpha,1.5\n2,beta,2.5\n3,gamma,3.5\n"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=cwd, check=True, capture_output=True)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())
    return path


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fixwitness-test-"))
        self._old = os.getcwd()

    def tearDown(self):
        os.chdir(self._old)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def repo(self, files: dict[str, str]) -> Path:
        repo = self.tmp / "repo"
        for rel, text in files.items():
            write(repo / rel, text)
        git(repo, "init", "-q")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "original")
        return repo

    def check(self, **settings):
        return run_check(load_config(None, settings))


# ---------------------------------------------------------------- unit tests

class CaseGenerationTests(unittest.TestCase):
    S = SAMPLE.encode()

    def test_deterministic(self):
        a, b = generate_cases(self.S, seed=7), generate_cases(self.S, seed=7)
        self.assertEqual([(c.id, c.value, c.content) for c in a], [(c.id, c.value, c.content) for c in b])

    def test_numeric_column_gets_numeric_formats(self):
        cats = {c.category for c in generate_cases(self.S, columns=["amount"])}
        self.assertIn("numeric-format", cats)
        self.assertNotIn("unicode", cats)

    def test_attack_families_and_canaries(self):
        attacks = [c for c in generate_cases(self.S, columns=["name"], canary_dir="/tmp/x") if c.kind == "attack"]
        self.assertEqual({c.family for c in attacks},
                         {"command-injection", "code-injection", "path-traversal", "template-injection"})
        files = [c for c in attacks if c.oracle == "file"]
        self.assertEqual(len({c.canary for c in files}), len(files))
        for c in files:
            self.assertTrue(c.canary.startswith(CANARY_PREFIX))
            self.assertIn(c.canary.encode(), c.content)
        self.assertTrue(any(b"/tmp/x/" in c.content for c in files if c.family == "command-injection"))

    def test_date_and_duplicate_categories(self):
        s = b"id,day,amount\n1,2026-01-02,1\n2,2026-02-03,2\n3,2026-03-04,3\n"
        cases = generate_cases(s, columns=["day"])
        cats = {c.category for c in cases}
        self.assertIn("date-format", cats)
        self.assertIn("duplicate", cats)
        self.assertNotIn("unicode", cats)

    def test_review_category_changes_kind(self):
        cases = generate_cases(self.S, columns=["name"], review=["quotes"])
        self.assertEqual({c.kind for c in cases if c.category == "quotes"}, {"review"})

    def test_cap_keeps_attacks_and_file_cases(self):
        capped = generate_cases(self.S, columns=["amount"], max_cases=20)
        self.assertEqual(len(capped), 20)
        self.assertEqual(sum(c.kind == "attack" for c in capped), 13)
        self.assertEqual(sum(c.category == "file-structure" for c in capped), 3)

    def test_unknown_column(self):
        with self.assertRaises(ValueError):
            generate_cases(self.S, columns=["missing"])

    def test_structural_cases(self):
        incident = b"id;name;amount_v2;amount\n9;z;1;2\n"
        cases = generate_cases(self.S, incident=incident, attacks=False)
        by_cat = {}
        for c in cases:
            by_cat.setdefault(c.category, []).append(c)
        # schema: the incident's new column added to data the job already handles, and reordered columns
        added = [c for c in by_cat["schema"] if "amount_v2" in c.value]
        self.assertTrue(added)
        self.assertTrue(added[0].content.startswith(b"id,name,amount,amount_v2\n"))
        self.assertTrue(any("reverse" in c.value for c in by_cat["schema"]))
        # header-names: for every other delimiter, a header line with more of it than commas
        firsts = [c.content.decode().split("\n", 1)[0] for c in by_cat["header-names"]]
        for d in (";", "\t", "|"):
            self.assertTrue(any(f.count(d) > f.count(",") for f in firsts), d)
            # and a header record whose first physical line has the delimiter but no comma
            self.assertTrue(any(d in f and "," not in f for f in firsts), d)
        # delimiter-mix: quoted and unquoted forms, in a text column and in an added column
        values = {c.value for c in by_cat["delimiter-mix"]}
        self.assertIn('a; "b"', values)
        self.assertIn('a; "b" (unquoted)', values)
        self.assertTrue(any("added 'note' column" in v for v in values))

    def test_delimiter_mix_follows_review_of_its_characters(self):
        reviewed = generate_cases(self.S, columns=["name"], review=["shell-metachar", "quotes"], attacks=False)
        kinds = {c.value: c.kind for c in reviewed if c.category == "delimiter-mix"}
        self.assertEqual(kinds['a; "b"'], "review")           # ; and quotes
        self.assertEqual(kinds["a|b|c (unquoted)"], "review")   # | is a shell metacharacter
        self.assertEqual(kinds["a\tb\tc"], "valid")             # tabs only: neither category
        plain = generate_cases(self.S, columns=["name"], attacks=False)
        self.assertEqual({c.kind for c in plain if c.category == "delimiter-mix"}, {"valid"})

    def test_structural_cases_without_incident(self):
        cats = {c.category for c in generate_cases(self.S, columns=["amount"], attacks=False)}
        self.assertTrue({"schema", "header-names", "delimiter-mix"} <= cats)


class CompareTests(unittest.TestCase):
    def test_identical_and_same_data(self):
        o = CompareOptions()
        self.assertEqual(compare(b"a,b\n1,2\n", b"a,b\n1,2\n", o)[0], "identical")
        self.assertEqual(compare(b"a,b\n1,2\n", b'"a","b"\r\n"1","2"\r\n', o)[0], "same-data")

    def test_changed_reports_cell(self):
        status, details = compare(b"a,b\n1,2\n", b"a,b\n1,2.0\n", CompareOptions())
        self.assertEqual(status, "changed")
        self.assertIn("'2' -> '2.0'", details[0])

    def test_tolerance_unordered_ignore(self):
        self.assertEqual(compare(b"a\n0.1\n", b"a\n0.1000000001\n", CompareOptions(tolerance=1e-6))[0], "same-data")
        self.assertEqual(compare(b"a\n1\n2\n", b"a\n2\n1\n", CompareOptions(unordered=True))[0], "same-data")
        self.assertEqual(compare(b"a,t\n1,x\n", b"a,t\n1,y\n", CompareOptions(ignore_columns={"t"}))[0], "same-data")
        import re
        o = CompareOptions(ignore_patterns=[re.compile(r"\d{4}-\d\d-\d\d")])
        self.assertEqual(compare(b"a\nrun 2026-01-01\n", b"a\nrun 2026-02-02\n", o)[0], "same-data")

    def test_unstable_columns(self):
        cols, problem = unstable_columns(b"a,t\n1,x\n", b"a,t\n1,y\n")
        self.assertEqual((cols, problem), ({"t"}, None))


class RunnerTests(TempDirTest):
    def test_disallowed_program_and_shell_operators(self):
        with self.assertRaises(RunConfigError):
            build_command("curl {script} {input}", "s", "i", "o", allow_any=False)
        with self.assertRaises(RunConfigError):
            build_command("python3 {script} {input} | tee x", "s", "i", "o", allow_any=False)
        with self.assertRaises(RunConfigError):
            build_command("python3 {input}", "s", "i", "o", allow_any=False)

    def test_stdin_and_stdout_forms(self):
        cmd = build_command("python3 {script} < {input}", "s.py", "in.csv", "out.csv", False)
        self.assertEqual((cmd.argv, cmd.stdin_from_input, cmd.output_from), (["python3", "s.py"], True, "stdout"))
        cmd = build_command("python3 {script} {input} {output}", "a b;rm", "in", "out", False)
        self.assertEqual(cmd.argv[1], "a b;rm")
        self.assertEqual(cmd.output_from, "file")

    def test_timeout_kills_background_children(self):
        script = write(self.tmp / "slow.sh", "sleep 31.4159 &\nsleep 31.4159\n")
        inv = Invocation(template="bash {script} {input}", timeout=1)
        start = time.time()
        result = run_side(inv, Side("original", None, script), self.tmp / "case", b"x\n")
        self.assertTrue(result.timed_out)
        self.assertLess(time.time() - start, 10)
        time.sleep(0.3)
        left = subprocess.run(["pgrep", "-f", "sleep 31.4159"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(left, "", "background processes must be killed")

    @unittest.skipUnless(no_network_available(), "needs unprivileged user namespaces")
    def test_no_network(self):
        script = write(self.tmp / "net.py", """
            import socket, sys
            try:
                socket.create_connection(("10.255.255.1", 80), timeout=2)
                print("net-ok")
            except OSError:
                print("net-blocked")
        """)
        inv = Invocation(template="python3 {script} {input}", no_network=True)
        result = run_side(inv, Side("original", None, script), self.tmp / "case", b"x\n")
        self.assertEqual(result.stdout.strip(), b"net-blocked")


class ScoreTests(unittest.TestCase):
    def test_score(self):
        self.assertEqual(confidence("FAIL", 100, True)["score"], 0)
        self.assertEqual(confidence("PASS", 30, True)["score"], 90)
        self.assertEqual(confidence("PASS", 30, False)["score"], 63)


class ConfigTests(unittest.TestCase):
    def test_unknown_setting_and_missing_target(self):
        with self.assertRaises(ConfigError):
            load_config(None, {"path": "x.py", "nonsense": 1})
        load_config(None, {})  # no file named: valid, it checks every change in the working tree
        with self.assertRaises(ConfigError):
            load_config(None, {}).require_target()  # ... but a single check needs one
        with self.assertRaises(ConfigError):
            load_config(None, {"before": "a.py"})


# ---------------------------------------------------------------- end to end

class ExampleBase(TempDirTest):
    def setUp(self):
        super().setUp()
        shutil.copytree(EXAMPLES, self.tmp / "examples")

    def example(self, folder, after):
        cfg = load_config(self.tmp / "examples" / folder / "fixwitness.toml",
                          {"after": str(self.tmp / "examples" / folder / after)})
        return run_check(cfg)


class ExampleTests(ExampleBase):
    def test_python_naive_fails_safe_passes(self):
        naive = self.example("python_eval", "clean_amounts_fix_naive.py")
        self.assertEqual(naive["verdict"], "FAIL")
        self.assertEqual(naive["cases"][0]["status"], "identical", "naive fix looks fine on the sample alone")
        safe = self.example("python_eval", "clean_amounts_fix_safe.py")
        self.assertEqual(safe["verdict"], "PASS")
        self.assertIn("code-injection", safe["security"]["families_reproduced"])
        self.assertGreaterEqual(safe["confidence"]["score"], 90)

    def test_shell_naive_fails_safe_passes(self):
        self.assertEqual(self.example("shell_eval", "normalize_regions_fix_naive.sh")["verdict"], "FAIL")
        safe = self.example("shell_eval", "normalize_regions_fix_safe.sh")
        self.assertEqual(safe["verdict"], "PASS")
        self.assertIn("command-injection", safe["security"]["families_reproduced"])

    def test_unfixed_script_is_still_exploitable(self):
        proof = self.example("python_eval", "clean_amounts.py")
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertFalse(proof["security"]["hole_closed"])

    def test_replay_and_tampering(self):
        proof = self.example("python_eval", "clean_amounts_fix_safe.py")
        self.assertTrue(replay(proof)["reproduced"])
        after = Path(proof["replay"]["after"])
        after.write_text(after.read_text() + "\n# edited\n")
        result = replay(proof)
        self.assertFalse(result["reproduced"])
        self.assertIn("changed", result["problems"][0])


class RepairModeTests(ExampleBase):
    def test_naive_repair_goes_green_but_turns_refunds_into_charges(self):
        proof = self.example("pipeline_repair", "load_payments_repair_naive.py")
        self.assertEqual((proof["incident"]["file"], proof["incident"]["status"]), ("incident.csv", "resolved"))
        self.assertIn("one row per input row", proof["incident"]["checks"])
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertFalse(proof["security"]["checked"])
        details = " ".join(" ".join(d["details"]) for d in proof["differences"])
        self.assertIn("'-300' -> '300'", details)

    def test_safe_repair_passes(self):
        proof = self.example("pipeline_repair", "load_payments_repair_safe.py")
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertEqual(proof["incident"]["status"], "resolved")
        self.assertEqual(proof["confidence"]["components"]["reproduction_factor"], 1.0)
        self.assertGreaterEqual(proof["confidence"]["score"], 90)
        self.assertEqual(proof["security"]["payloads"], 0)

    def test_unrepaired_job_still_fails(self):
        proof = self.example("pipeline_repair", "load_payments.py")
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertEqual(proof["incident"]["status"], "still-failing")

    def test_replay_checks_incident_file(self):
        proof = self.example("pipeline_repair", "load_payments_repair_safe.py")
        self.assertTrue(replay(proof)["reproduced"])
        inc = Path(proof["replay"]["incident"])
        inc.write_text(inc.read_text() + "P-9,Z,1.00\n")
        self.assertIn("incident", " ".join(replay(proof)["problems"]))

    def _repair(self, body: str, **extra):
        ex = self.tmp / "examples" / "pipeline_repair"
        write(ex / "repair_x.py", body)
        return run_check(load_config(ex / "fixwitness.toml", {"after": str(ex / "repair_x.py"), **extra}))

    REPAIR = """
        import csv, sys
        src, dst = sys.argv[1], sys.argv[2]
        with open(src, newline="", encoding="utf-8") as f, open(dst, "w", newline="", encoding="utf-8") as g:
            reader = csv.DictReader(f)
            writer = csv.DictWriter(g, fieldnames=reader.fieldnames + ["amount_cents"])
            writer.writeheader()
            for row in reader:
                try:
                    amount = float(row["amount"])
                except ValueError:
                    {handler}
                row["amount_cents"] = round(amount * 100)
                writer.writerow(row)
    """

    def test_repair_that_drops_rows_fails(self):
        proof = self._repair(self.REPAIR.replace("{handler}", "continue"))
        self.assertEqual(proof["incident"]["status"], "resolved-incorrectly")
        self.assertIn("rows were dropped", " ".join(proof["reasons"]))
        self.assertEqual(proof["verdict"], "FAIL")

    def test_repair_that_fills_zero_needs_expected_output(self):
        body = self.REPAIR.replace("{handler}", "amount = 0.0")
        self.assertEqual(self._repair(body)["verdict"], "PASS")  # invisible without the right answer
        ex = self.tmp / "examples" / "pipeline_repair"
        write(ex / "expected.csv", "payment_id,customer,amount,amount_cents\nP-3001,Acme Ltd,125.00,12500\n"
                                   "P-3002,Globex,\"1,250.00\",125000\nP-3003,Initech,42.75,4275\n")
        proof = self._repair(body, incident_expected=str(ex / "expected.csv"))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertEqual(proof["incident"]["status"], "resolved-incorrectly")
        safe = run_check(load_config(ex / "fixwitness.toml", {"incident_expected": str(ex / "expected.csv")}))
        self.assertEqual(safe["verdict"], "PASS", safe["reasons"])

    def test_attacks_off_generates_no_payloads(self):
        cases = generate_cases(SAMPLE.encode(), attacks=False)
        self.assertFalse([c for c in cases if c.kind == "attack"])


class StructuralRepairTests(TempDirTest):
    """Repairs that pass on the sample and the incident but change files the job already handled."""

    JOB = """
        import csv, sys

        def open_rows(f):
            {open_rows}

        def column(r):
            {column}

        with open(sys.argv[1], newline="") as f, open(sys.argv[2], "w", newline="") as g:
            w = csv.writer(g)
            w.writerow(["id", "cents"])
            for r in open_rows(f):
                w.writerow([r["id"], round(float(r[column(r)]) * 100)])
    """
    BY_NAME = "return csv.DictReader(f)"
    PRICE = 'return "price"'

    def _job(self, after_open=BY_NAME, after_column=PRICE, incident=""):
        write(self.tmp / "s.csv", "id,item,price\n1,pen,1.50\n2,ink,2.25\n3,pad,3.00\n")
        write(self.tmp / "inc.csv", incident)
        job = textwrap.dedent(self.JOB)
        write(self.tmp / "b.py", job.replace("{open_rows}", self.BY_NAME).replace("{column}", self.PRICE))
        write(self.tmp / "a.py", job.replace("{open_rows}", after_open).replace("{column}", after_column))
        return self.check(before=str(self.tmp / "b.py"), after=str(self.tmp / "a.py"),
                          sample=str(self.tmp / "s.csv"), incident=str(self.tmp / "inc.csv"),
                          attacks=False, output="csv")

    def test_fix_that_prefers_the_new_column_fails(self):
        incident = "id,item,price_eur\n7,cap,4.00\n"
        proof = self._job(after_column='return "price_eur" if "price_eur" in r else "price"', incident=incident)
        self.assertEqual(proof["incident"]["status"], "resolved")
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("schema", {d["category"] for d in proof["differences"]})
        good = self._job(after_column='return "price" if "price" in r else "price_eur"', incident=incident)
        self.assertEqual(good["verdict"], "PASS", good["reasons"])

    def test_fix_that_guesses_the_delimiter_from_the_first_line_fails(self):
        incident = "id;item;price\n7;cap;4.00\n"
        guess = ('h = f.readline(); f.seek(0); '
                 'return csv.DictReader(f, delimiter=";" if h.count(";") > h.count(",") else ",")')
        proof = self._job(after_open=guess, incident=incident)
        self.assertEqual(proof["incident"]["status"], "resolved")
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("header-names", {d["category"] for d in proof["differences"]})
        retry = ('text = f.read(); rows = list(csv.DictReader(text.splitlines())); '
                 'return rows if rows and "price" in rows[0] else list(csv.DictReader(text.splitlines(), delimiter=";"))')
        good = self._job(after_open=retry, incident=incident)
        self.assertEqual(good["verdict"], "PASS", good["reasons"])

    def test_fix_that_sniffs_the_delimiter_fails(self):
        incident = "id;item;price\n7;cap;4.00\n"
        sniff = ('d = csv.Sniffer().sniff(f.read(4096), delimiters=",;").delimiter; f.seek(0); '
                 'return csv.DictReader(f, delimiter=d)')
        proof = self._job(after_open=sniff, incident=incident)
        self.assertEqual(proof["incident"]["status"], "resolved")
        self.assertEqual(proof["verdict"], "FAIL")


class RewriteTests(TempDirTest):
    def test_shell_script_rewritten_in_python(self):
        shutil.copy(EXAMPLES / "shell_eval" / "normalize_regions_fix_safe.sh", self.tmp / "legacy.sh")
        shutil.copy(EXAMPLES / "shell_eval" / "sample.csv", self.tmp / "sample.csv")
        good = """
            import string, sys
            UP = str.maketrans(string.ascii_lowercase, string.ascii_uppercase)
            lines = open(sys.argv[1], newline="").read().split("\\n")
            with open(sys.argv[2], "w", newline="") as g:
                g.write(lines[0] + "\\n")
                for line in lines[1:]:
                    if line:
                        rid, region, amount = (line.split(",", 2) + ["", ""])[:3]
                        g.write(f"{rid},{' '.join(region.split()).translate(UP)},{amount}\\n")
        """
        write(self.tmp / "rewrite.py", good)
        args = dict(before=str(self.tmp / "legacy.sh"), after=str(self.tmp / "rewrite.py"), columns=["region"],
                    attacks=False)
        proof = self.check(**args)
        self.assertEqual(proof["config"]["run"], "bash {script} {input} {output}")
        self.assertEqual(proof["config"]["run_after"], "python3 {script} {input} {output}")
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        write(self.tmp / "rewrite.py", good.replace("' '.join(region.split())", "region.strip()"))
        self.assertEqual(self.check(**args)["verdict"], "FAIL")


class AutoDetectTests(TempDirTest):
    def test_stdout_and_stdin_scripts_are_detected(self):
        write(self.tmp / "s.csv", SAMPLE)
        write(self.tmp / "out_before.py", """
            import csv, sys
            for r in csv.DictReader(open(sys.argv[1])):
                print(r["id"], eval(r["amount"]))
        """)
        write(self.tmp / "out_after.py", """
            import csv, sys
            for r in csv.DictReader(open(sys.argv[1])):
                s = r["amount"].strip()
                try:
                    v = int(s, 0)
                except ValueError:
                    v = float(s)
                print(r["id"], v)
        """)
        proof = self.check(before=str(self.tmp / "out_before.py"), after=str(self.tmp / "out_after.py"),
                           columns=["amount"])
        self.assertEqual(proof["config"]["run"], "python3 {script} {input}")
        self.assertEqual(proof["verdict"], "PASS")

        write(self.tmp / "in_before.py", "import sys\nfor line in sys.stdin: print(eval(line.split(',')[2]) if line[0].isdigit() else line.strip())\n")
        write(self.tmp / "in_after.py", "import sys\nfor line in sys.stdin: print(float(line.split(',')[2]) if line[0].isdigit() else line.strip())\n")
        summary = dry_run(load_config(None, {"before": str(self.tmp / "in_before.py"),
                                             "after": str(self.tmp / "in_after.py")}))
        self.assertEqual(summary["run"], "python3 {script} < {input}")
        self.assertIn("sample: found s.csv", " ".join(summary["notes"]))

    def test_sample_discovery_errors(self):
        write(self.tmp / "a.py", "print(1)\n")
        write(self.tmp / "b.py", "print(1)\n")
        with self.assertRaises(PlanError):
            dry_run(load_config(None, {"before": str(self.tmp / "a.py"), "after": str(self.tmp / "b.py")}))
        write(self.tmp / "x.csv", SAMPLE)
        write(self.tmp / "y.csv", SAMPLE)
        with self.assertRaises(PlanError) as ctx:
            dry_run(load_config(None, {"before": str(self.tmp / "a.py"), "after": str(self.tmp / "b.py")}))
        self.assertIn("several files could be the sample", str(ctx.exception))


class RobustnessTests(TempDirTest):
    def test_nondeterministic_column_is_ignored(self):
        write(self.tmp / "s.csv", SAMPLE)
        body = """
            import csv, sys, uuid
            r = csv.DictReader(open(sys.argv[1])); w = csv.writer(open(sys.argv[2], "w", newline=""))
            w.writerow(["id", "amount", "run_id"])
            for row in r:
                w.writerow([row["id"], {expr}, uuid.uuid4().hex])
        """
        write(self.tmp / "b.py", body.replace("{expr}", "eval(row['amount'])"))
        helper = "def num(s):\n    s = s.strip()\n    try:\n        return int(s, 0)\n    except ValueError:\n        return float(s)\n"
        (self.tmp / "a.py").write_text(helper + textwrap.dedent(body).lstrip().replace("{expr}", "num(row['amount'])"))
        args = dict(before=str(self.tmp / "b.py"), after=str(self.tmp / "a.py"), sample=str(self.tmp / "s.csv"),
                    columns=["amount"])
        proof = self.check(**args)
        self.assertEqual(proof["config"]["auto_ignored_columns"], ["run_id"])
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertEqual(self.check(**args, auto_ignore_unstable=False)["verdict"], "FAIL")

    def test_tolerance_and_unordered(self):
        write(self.tmp / "s.csv", "id,x\n1,1.5\n2,2.5\n3,3.5\n")
        write(self.tmp / "b.py", """
            import csv, sys
            rows = list(csv.DictReader(open(sys.argv[1])))
            print("id,y")
            for r in rows: print(r["id"] + "," + repr(round(float(r["x"]) * 0.1, 12)))
        """)
        write(self.tmp / "a.py", """
            import csv, sys
            rows = list(csv.DictReader(open(sys.argv[1])))
            print("id,y")
            for r in reversed(rows): print(r["id"] + "," + repr(float(r["x"]) / 10))
        """)
        args = dict(before=str(self.tmp / "b.py"), after=str(self.tmp / "a.py"), sample=str(self.tmp / "s.csv"),
                    columns=["x"], output="csv")
        self.assertEqual(self.check(**args)["verdict"], "FAIL")
        self.assertEqual(self.check(**args, tolerance=1e-9, unordered=True)["verdict"], "PASS")

    def test_template_and_path_traversal_payloads(self):
        write(self.tmp / "s.csv", "id,region\n1,north\n2,south\n3,east\n")
        write(self.tmp / "b.py", """
            import csv, os, re, sys
            os.makedirs("parts", exist_ok=True)
            out = open(sys.argv[2], "w")
            out.write("id,label\\n")
            for r in csv.DictReader(open(sys.argv[1])):
                label = re.sub(r"\\{\\{(.*?)\\}\\}", lambda m: str(eval(m.group(1), {"__builtins__": {}})), r["region"])
                open(os.path.join("parts", r["region"] + ".txt"), "w").write(r["id"])
                out.write(r["id"] + "," + label.replace(",", " ").replace("\\n", " ") + "\\n")
        """)
        write(self.tmp / "a.py", """
            import csv, os, sys
            os.makedirs("parts", exist_ok=True)
            out = open(sys.argv[2], "w")
            out.write("id,label\\n")
            for r in csv.DictReader(open(sys.argv[1])):
                open(os.path.join("parts", os.path.basename(r["region"]) + ".txt"), "w").write(r["id"])
                out.write(r["id"] + "," + r["region"].replace(",", " ").replace("\\n", " ") + "\\n")
        """)
        proof = self.check(before=str(self.tmp / "b.py"), after=str(self.tmp / "a.py"),
                           sample=str(self.tmp / "s.csv"), columns=["region"])
        fams = set(proof["security"]["families_reproduced"])
        self.assertIn("template-injection", fams)
        self.assertIn("path-traversal", fams)
        self.assertTrue(proof["security"]["hole_closed"])


class GitModeTests(TempDirTest):
    BEFORE = """
        import csv, sys
        src, dst = sys.argv[1], sys.argv[2]
        with open(src, newline="") as f, open(dst, "w", newline="") as g:
            r = csv.DictReader(f); w = csv.DictWriter(g, fieldnames=r.fieldnames)
            w.writeheader()
            for row in r:
                row["amount"] = eval(row["amount"])
                w.writerow(row)
    """
    SAFE = BEFORE.replace('eval(row["amount"])', 'num(row["amount"])').replace(
        "import csv, sys", "import csv, sys\n"
        "        def num(s):\n            s = s.strip()\n            try:\n                return int(s, 0)\n"
        "            except ValueError:\n                return float(s)")

    def test_one_line_usage(self):
        repo = self.repo({"etl/clean.py": self.BEFORE, "etl/sample.csv": SAMPLE})
        write(repo / "etl/clean.py", self.SAFE)
        os.chdir(repo)
        proof = self.check(path="etl/clean.py", columns=["amount"])
        self.assertEqual(proof["inputs"]["mode"], "git")
        self.assertEqual(proof["inputs"]["target"], "etl/clean.py")
        self.assertEqual(proof["config"]["run"], "python3 {script} {input} {output}")
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        from fixwitness.report import write_outputs
        path = write_outputs(proof, repo / ".fixwitness")
        self.assertTrue(replay(json.loads(path.read_text()))["reproduced"], "proof output must not affect replay")

    def test_multi_file_fix_with_command(self):
        repo = self.repo({
            "etl/run.py": "import sys\nfrom helpers import parse\nimport csv\n"
                          "r = csv.DictReader(open(sys.argv[1]))\nprint('id,amount')\n"
                          "for row in r: print(row['id'] + ',' + str(parse(row['amount'])))\n",
            "etl/helpers.py": "def parse(s):\n    return eval(s)\n",
            "data/sample.csv": SAMPLE,
        })
        write(repo / "etl/helpers.py", "def parse(s):\n    return float(s)\n")
        os.chdir(repo)
        proof = self.check(command="python3 etl/run.py {input}", sample="data/sample.csv", columns=["amount"])
        self.assertEqual([c["path"] for c in proof["inputs"]["changed"]], ["etl/helpers.py"])
        self.assertEqual(proof["verdict"], "FAIL")  # float() turns 1200 into 1200.0
        self.assertTrue(proof["security"]["hole_closed"])

    def test_no_changes_is_an_error(self):
        repo = self.repo({"etl/clean.py": self.BEFORE, "etl/sample.csv": SAMPLE})
        os.chdir(repo)
        with self.assertRaises(PlanError):
            self.check(path="etl/clean.py")


ORDERS = "order_id,customer_id,amount,status\n1,10,12.50,paid\n2,10,300.75,paid\n3,11,99.99,refunded\n4,12,5.25,paid\n"
CUSTOMERS = "customer_id,name,region\n10,Acme Ltd,east\n11,Globex,west\n12,Initech,east\n"
REVENUE = """
    select c.region, sum(o.amount) as revenue, count(*) as orders
    from orders o
    join customers c on c.customer_id = o.customer_id
    where o.status = 'paid'
    group by c.region
"""


class SqlUnitTests(unittest.TestCase):
    def test_run_query_types_nulls_and_order(self):
        from fixwitness.sql import make_bundle, run_query, table_types
        t = {"orders": ORDERS.replace("5.25", "").encode()}
        types = {"orders": table_types(ORDERS.encode())}
        self.assertEqual(types["orders"], {"order_id": "integer", "customer_id": "integer", "amount": "number",
                                           "status": "text"})
        out = run_query("select order_id, amount from orders order by order_id desc", make_bundle(t, types),
                        engine="sqlite", ordered=True).decode()
        self.assertEqual(out.splitlines(), ["order_id,amount", "4,", "3,99.99", "2,300.75", "1,12.5"])
        unordered = run_query("select order_id from orders order by order_id desc", make_bundle(t, types),
                              engine="sqlite").decode()
        self.assertEqual(unordered.splitlines()[1:], ["1", "2", "3", "4"])  # compared as a set: sorted

    def test_values_that_do_not_fit_the_column_type_fail_the_load(self):
        from fixwitness.sql import SqlError, make_bundle, run_query, table_types
        types = {"orders": table_types(ORDERS.encode())}
        bad = make_bundle({"orders": ORDERS.replace("12.50", '"1,250"').encode()}, types)
        with self.assertRaises(SqlError):
            run_query("select * from orders", bad, engine="sqlite")

    def test_dbt_rendering(self):
        from fixwitness.sql import SqlError, render_dbt
        sql = "{{ config(materialized='table') }}\nselect * from {{ ref('stg_orders') }} o " \
              "join {{ source('crm', 'customers') }} c using (customer_id) {# note #}"
        self.assertEqual(render_dbt(sql).strip(), "select * from stg_orders o join customers c using (customer_id)")
        self.assertEqual(render_dbt("select * from {{ ref('pkg', 'model_x') }}").strip(), "select * from model_x")
        with self.assertRaises(SqlError):
            render_dbt("select {{ dbt_utils.star(ref('x')) }} from t")
        with self.assertRaises(SqlError):
            render_dbt("{% if is_incremental() %} where 1=1 {% endif %}")

    def test_cases_vary_one_table_at_a_time_and_skip_unloadable(self):
        from fixwitness.sql import generate_sql_cases, read_bundle, table_types
        tables = {"orders": ORDERS.encode(), "customers": CUSTOMERS.encode()}
        types = {k: table_types(v) for k, v in tables.items()}
        cases = generate_sql_cases(tables, types, rows=3, max_cases=300)
        self.assertTrue(cases)
        for c in cases:
            got, _ = read_bundle(c.content)
            changed = [t for t in tables if got[t].encode() != tables[t]]
            self.assertLessEqual(len(changed), 1, c.value)
        self.assertTrue(any(c.column == "customers.customer_id" and c.category == "duplicate" for c in cases))
        self.assertFalse(any(c.category == "header-names" for c in cases))
        only = generate_sql_cases(tables, types, columns=["orders.amount"])
        self.assertEqual({c.column for c in only} - {"orders"}, {"orders.amount"})
        with self.assertRaises(ValueError):
            generate_sql_cases(tables, types, columns=["customer_id"])  # in both tables: ambiguous


class LinkedKeysTests(TempDirTest):
    """Samples taken table by table rarely join; their keys are linked so join logic is exercised."""
    ORD = "order_id,customer_id,amount\n1,90,10\n2,91,20\n3,92,30\n4,93,40\n"
    CUS = "id,region\n1,EU\n2,US\n3,EU\n"

    def test_link_tables(self):
        from fixwitness.sql import link_tables, table_types
        tables = {"orders": self.ORD.encode(), "customers": self.CUS.encode()}
        types = {t: table_types(v) for t, v in tables.items()}
        linked, links = link_tables(tables, types)
        self.assertEqual(links, ["orders.customer_id -> customers.id"])
        self.assertIn(b"1,1,10\n2,2,20\n3,3,30\n4,1,40", linked["orders"])  # cycles over the first 3 keys
        self.assertEqual(linked["customers"], tables["customers"])
        self.assertEqual(link_tables(linked, types)[1], [])  # keys that already join are left alone
        both = {"orders": self.ORD.encode(), "customers": self.CUS.encode(), "customer": self.CUS.encode()}
        self.assertEqual(link_tables(both, {t: table_types(v) for t, v in both.items()})[1], [])  # ambiguous

    def test_join_logic_change_is_seen_only_with_linked_keys(self):
        write(self.tmp / "orders.csv", self.ORD)
        write(self.tmp / "customers.csv", self.CUS)
        before = "select c.region, sum(o.amount) as total from orders o join customers c on c.id = o.customer_id group by c.region"
        write(self.tmp / "before.sql", before)
        write(self.tmp / "after.sql", before.replace("group by", "where c.region <> 'US' group by"))
        proof = self.check(before=str(self.tmp / "before.sql"), after=str(self.tmp / "after.sql"), engine="sqlite",
                           tables={"orders": str(self.tmp / "orders.csv"), "customers": str(self.tmp / "customers.csv")})
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertTrue(any("did not join" in n and "orders.customer_id -> customers.id" in n for n in proof["notes"]))
        self.assertEqual(proof["cases"][0]["status"], "identical")  # the tables as given: nothing joins


class DbtWarehouseUnitTests(TempDirTest):
    def test_profile_keeps_secrets_out(self):
        from fixwitness.dbtmode import _warehouse_profile
        path = self.tmp / "profiles.yml"
        kind = _warehouse_profile(path, "shop", "postgres://ci@db.internal:5433/analytics", "fw_0123456789")
        text = path.read_text()
        self.assertEqual(kind, "postgres")
        for want in ("type: postgres", 'host: "db.internal"', "port: 5433", 'dbname: "analytics"',
                     'schema: "fw_0123456789"', "env_var('PGPASSWORD'"):
            self.assertIn(want, text)
        from fixwitness.warehouse import WarehouseError
        with self.assertRaises(WarehouseError):
            _warehouse_profile(path, "shop", "postgres://ci:secret@db/analytics", "fw_0123456789")

    def test_schema_variable(self):
        from fixwitness.dbtmode import schema_variable
        write(self.tmp / "dbt_project.yml", "name: z\nvars:\n  zendesk_schema: zendesk_integration_tests\n"
                                            "  zendesk:\n    zendesk_ticket_identifier: \"ticket_data\"\n")
        self.assertEqual(schema_variable(self.tmp, "zendesk_integration_tests"), "zendesk_schema")
        self.assertIsNone(schema_variable(self.tmp, "other"))

    def test_reserved_words_are_quoted(self):
        from fixwitness.warehouse import ident
        self.assertEqual(ident("orders", "postgres"), "orders")
        self.assertEqual(ident("user", "postgres"), '"user"')
        self.assertEqual(ident("default", "postgres"), '"default"')
        self.assertEqual(ident("end", "bigquery"), "`end`")
        self.assertEqual(ident("Order Total", "postgres"), '"Order Total"')
        self.assertEqual(ident("Amount", "postgres", exact=True), '"Amount"')

    def test_targets_named_after_the_adapter(self):
        from fixwitness.dbtmode import _profile, _warehouse_profile
        _profile(self.tmp / "a.yml", "shop", self.tmp / "x.duckdb", "main")
        self.assertIn("target: duckdb", (self.tmp / "a.yml").read_text())
        _warehouse_profile(self.tmp / "b.yml", "shop", "postgres://ci@h/db", "fw_0123456789")
        self.assertIn("target: postgres", (self.tmp / "b.yml").read_text())

    def test_private_schemas_only(self):
        from fixwitness.warehouse import WarehouseError, _schemas
        with self.assertRaises(WarehouseError):
            _schemas("postgres://ci@localhost/test", "analytics")

    def test_compile_cache(self):
        from fixwitness import dbtmode
        tree = self.tmp / "tree"
        write(tree / "proj/dbt_project.yml", "name: p\n")
        write(tree / "proj/models/a.sql", "select 1 as x\n")
        write(tree / "proj/target/manifest.json", "{}")  # build output: not part of the key
        k1 = dbtmode.tree_key(tree, tree / "proj", None)
        write(tree / "proj/target/run_results.json", "{}")
        self.assertEqual(dbtmode.tree_key(tree, tree / "proj", None), k1)
        self.assertNotEqual(dbtmode.tree_key(tree, tree / "proj", "postgres://ci@h/db"), k1)
        write(tree / "proj/models/a.sql", "select 2 as x\n")
        self.assertNotEqual(dbtmode.tree_key(tree, tree / "proj", None), k1)
        cache = self.tmp / "cache"
        old = os.environ.get(dbtmode.CACHE_ENV)
        os.environ[dbtmode.CACHE_ENV] = str(cache)
        try:
            key = dbtmode.tree_key(tree, tree / "proj", None)
            write(cache / "dbt" / key / "manifest.json", '{"cached": true}')
            notes = []
            got = dbtmode.compile_cached(tree, tree / "proj", self.tmp / "out", notes)
            self.assertEqual(json.loads(got.read_text()), {"cached": True})
            self.assertTrue(any("reused an identical earlier compile" in n for n in notes))
            os.environ[dbtmode.CACHE_ENV] = "off"
            self.assertIsNone(dbtmode.cache_dir())
        finally:
            if old is None:
                os.environ.pop(dbtmode.CACHE_ENV, None)
            else:
                os.environ[dbtmode.CACHE_ENV] = old

    def test_kinds_of_warehouse_types(self):
        from fixwitness.sql import kind_of
        for sql_type, kind in [("double precision", "number"), ("timestamp without time zone", "timestamp"),
                               ("character varying", "text"), ("NUMBER(38,0)", "integer"), ("NUMBER(18,2)", "number"),
                               ("INT64", "integer"), ("FLOAT64", "number"), ("BOOL", "boolean"),
                               ("TIMESTAMP_NTZ", "timestamp"), ("STRING", "text"), ("BIGNUMERIC", "number")]:
            self.assertEqual(kind_of(sql_type), kind, sql_type)


class DbtContractTests(TempDirTest):
    """The project's own dbt tests (unique, not_null, accepted_values) are rules on the inputs: a
    difference only on data that breaks them is reviewed, not failed."""
    R = staticmethod(lambda n: f'"memory"."main"."{n}"')

    def _manifest(self, stg_sql, mart_sql, tests=True):
        R = self.R

        def node(kind, name, code=None, deps=()):
            return {"resource_type": kind, "name": name, "package_name": "shop", "language": "sql",
                    "original_file_path": f"seeds/{name}.csv" if kind == "seed" else f"models/{name}.sql",
                    "relation_name": R(name), "config": {"materialized": "table"},
                    "depends_on": {"nodes": list(deps)}, **({"compiled_code": code} if code else {})}

        def test(name, test_name, model, column, **kw):
            return {"resource_type": "test", "name": name, "package_name": "shop", "config": {"enabled": True},
                    "attached_node": f"model.shop.{model}", "column_name": column,
                    "test_metadata": {"name": test_name, "kwargs": {"column_name": column, **kw}},
                    "depends_on": {"nodes": [f"model.shop.{model}"]}}

        nodes = {"seed.shop.raw_orders": node("seed", "raw_orders"),
                 "model.shop.stg_orders_tmp": node("model", "stg_orders_tmp", f"select * from {R('raw_orders')}",
                                                   ["seed.shop.raw_orders"]),
                 "model.shop.stg_orders": node("model", "stg_orders", stg_sql, ["model.shop.stg_orders_tmp"]),
                 "model.shop.revenue": node("model", "revenue", mart_sql, ["model.shop.stg_orders"])}
        if tests:
            nodes["test.shop.unique_stg_orders_order_id"] = test("unique_stg_orders_order_id", "unique", "stg_orders", "order_id")
            nodes["test.shop.not_null_stg_orders_order_id"] = test("not_null_stg_orders_order_id", "not_null", "stg_orders", "order_id")
            nodes["test.shop.accepted_values_stg_orders_status"] = test(
                "accepted_values_stg_orders_status", "accepted_values", "stg_orders", "status", values=["paid", "refunded"])
        return {"metadata": {"adapter_type": "duckdb", "project_name": "shop"}, "sources": {}, "nodes": nodes}

    STG = 'with base as (select * from {t}) select order_id as order_id, "amount", status from base'

    def _setup(self, tests=True):
        R = self.R
        write(self.tmp / "dbt_project.yml", "name: shop\nprofile: shop\n")
        write(self.tmp / "seeds/raw_orders.csv", "order_id,amount,status\n1,10,paid\n2,20,paid\n3,5,refunded\n")
        stg = self.STG.format(t=R("stg_orders_tmp"))
        sum_by_order = f"select status, sum(amount) as total, count(*) as n from {R('stg_orders')} group by status"
        # The refactor counts distinct orders: the same as count(*) unless an order_id repeats.
        changed = sum_by_order.replace("count(*)", "count(distinct order_id)")
        for name, mart in {"base": sum_by_order, "fix": changed}.items():
            (self.tmp / f"{name}.json").write_text(json.dumps(self._manifest(stg, mart, tests)))
        os.chdir(self.tmp)

    def test_contracts_traced_to_the_seed(self):
        from fixwitness.dbtmode import read_manifest
        self._setup()
        g = read_manifest(self.tmp / "base.json", self.tmp)
        got = sorted((c["table"], tuple(c["columns"]), c["test"]) for c in g.contracts)
        self.assertEqual(got, [("raw_orders", ("order_id",), "not_null"), ("raw_orders", ("order_id",), "unique"),
                               ("raw_orders", ("status",), "accepted_values")])

    def test_no_contract_through_a_filter(self):
        from fixwitness.dbtmode import read_manifest
        self._setup()
        data = json.loads((self.tmp / "base.json").read_text())
        data["nodes"]["model.shop.stg_orders"]["compiled_code"] += " where status <> 'void'"
        (self.tmp / "base.json").write_text(json.dumps(data))
        self.assertEqual(read_manifest(self.tmp / "base.json", self.tmp).contracts, [])

    def test_published_models_downstream_are_compared(self):
        """A mart that another mart reads is compared too; staging and intermediate models are not."""
        from fixwitness.dbtmode import Graph, compared_models
        g = Graph(adapter="duckdb")
        for name, path, deps in [("stg_a", "models/staging/stg_a.sql", []),
                                 ("int_b", "models/intermediate/int_b.sql", ["stg_a"]),
                                 ("interview_enhanced", "models/interview_enhanced.sql", ["int_b"]),
                                 ("stage_history", "models/stage_history.sql", ["interview_enhanced"]),
                                 ("other", "models/other.sql", [])]:
            g.models[name], g.paths[name], g.depends[name] = "select 1", path, set(deps)
        self.assertEqual(compared_models(g, ["int_b"]), ["interview_enhanced", "stage_history"])
        self.assertEqual(compared_models(g, ["stage_history"]), ["stage_history"])

    def test_contract_breaks(self):
        from fixwitness.sql import contract_breaks
        rules = [{"table": "t", "columns": ["id"], "test": "unique"}, {"table": "t", "columns": ["id"], "test": "not_null"},
                 {"table": "t", "columns": ["s"], "test": "accepted_values", "values": ["a"]}]
        self.assertEqual(contract_breaks({"t": "id,s\n1,a\n2,\n"}, rules), set())
        self.assertEqual(contract_breaks({"t": "id,s\n1,a\n1,a\n,b\n"}, rules), {0, 1, 2})

    def test_difference_only_on_broken_contract_is_reviewed(self):
        self._setup(tests=True)
        proof = self.check(manifest="fix.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertGreater(proof["behavior"]["review_differences"], 0)
        self.assertTrue(any("dbt tests are used as rules" in n for n in proof["notes"]), proof["notes"])
        self._setup(tests=False)
        proof = self.check(manifest="fix.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(proof["verdict"], "FAIL")


class DoctorTests(TempDirTest):
    def test_doctor_lists_what_would_be_checked_and_what_is_missing(self):
        from fixwitness.doctor import checks, render
        repo = self.repo({"etl/clean.py": "import sys\nprint(open(sys.argv[1]).read(), end='')\n",
                          "etl/data.csv": "id,amount\n1,2\n"})
        os.chdir(repo)
        write(repo / "etl/clean.py", "import sys\nprint(open(sys.argv[1]).read().upper(), end='')\n")
        items = checks(repo)
        text, ready = render(items)
        self.assertIn("will check etl/clean.py as script", text)
        self.assertIn("git base HEAD", text)
        self.assertEqual(ready, not any(i["status"] == "missing" for i in items))
        os.chdir(self.tmp)
        text, ready = render(checks(self.tmp))  # not a repository
        self.assertFalse(ready)
        self.assertIn("a git repository", text)


class ExpectChangeTests(TempDirTest):
    """A bug fix names the output columns it should change; anything else changing is a finding."""

    def _check(self, after_sql: str, expect: list[str]):
        write(self.tmp / "orders.csv", ORDERS)
        write(self.tmp / "customers.csv", CUSTOMERS)
        write(self.tmp / "before.sql", REVENUE)
        write(self.tmp / "after.sql", after_sql)
        return self.check(before=str(self.tmp / "before.sql"), after=str(self.tmp / "after.sql"), engine="sqlite",
                          tables={"orders": str(self.tmp / "orders.csv"), "customers": str(self.tmp / "customers.csv")},
                          expect_change=expect, max_cases=120)

    def test_only_the_expected_column_changes(self):
        proof = self._check(REVENUE.replace("count(*)", "count(o.amount)"), ["orders"])
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertGreater(proof["behavior"]["expected_change"], 0)
        self.assertTrue(any(c["status"] == "expected-change" for c in proof["cases"]))
        self.assertTrue(any("nothing else changes" in n for n in proof["notes"]))
        self.assertTrue(proof["expected_changes"] and proof["expected_changes"][0]["details"])
        from fixwitness.report import markdown
        self.assertIn("Expected change", markdown(proof))

    def test_something_else_changes_too(self):
        bad = REVENUE.replace("count(*)", "count(o.amount)").replace("sum(o.amount)", "sum(round(o.amount))")
        proof = self._check(bad, ["orders"])
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertTrue(any("changes more than orders" in r for r in proof["reasons"]), proof["reasons"])

    def test_the_expected_change_never_shows(self):
        proof = self._check(REVENUE.replace("count(*)", "count(1)"), ["orders"])
        self.assertEqual(proof["verdict"], "INCONCLUSIVE")
        self.assertTrue(any("did not show" in r for r in proof["reasons"]), proof["reasons"])


class UnstableOriginalTests(TempDirTest):
    """A difference on an input where the original's own output changes from run to run is not the
    change's: it is left out and reported, never failed."""
    SCRIPT = (
        "import csv, random, sys\n"
        "rows = list(csv.reader(open(sys.argv[1], newline='')))\n"
        "w = csv.writer(open(sys.argv[2], 'w', newline=''))\n"
        "w.writerow(rows[0] + ['pick'])\n"
        "for r in rows[1:]:\n"
        "    w.writerow(r + [random.random() if any(v == '' for v in r) else 0])  # a tie broken at random\n"
    )

    def test_original_unstable_on_some_inputs(self):
        write(self.tmp / "before.py", self.SCRIPT)
        write(self.tmp / "after.py", self.SCRIPT.replace("# a tie broken at random", "# same logic"))
        write(self.tmp / "sample.csv", "id,amount\n1,10\n2,20\n")
        proof = self.check(before=str(self.tmp / "before.py"), after=str(self.tmp / "after.py"),
                           sample=str(self.tmp / "sample.csv"), attacks=False, max_cases=80)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertGreater(proof["behavior"]["unstable"], 0)
        self.assertTrue(any("run to run" in w for w in proof["warnings"]))


class TypedColumnTests(TempDirTest):
    """Booleans and timestamps typed by dbt (or a warehouse) are loaded and varied as such."""

    def test_kinds_from_sql_types(self):
        from fixwitness.sql import kind_of
        for sql_type, kind in [("BIGINT", "integer"), ("INTEGER", "integer"), ("HUGEINT", "integer"),
                               ("DOUBLE", "number"), ("DECIMAL(18,3)", "number"), ("BOOLEAN", "boolean"),
                               ("DATE", "date"), ("TIMESTAMP", "timestamp"), ("TIMESTAMP WITH TIME ZONE", "timestamp"),
                               ("VARCHAR", "text"), ("JSON", "text")]:
            self.assertEqual(kind_of(sql_type), kind, sql_type)

    def test_timestamps_as_seeds_write_them(self):
        import datetime as dt
        from fixwitness.sql import SqlError, parse_timestamp
        self.assertEqual(parse_timestamp("2020-06-23 3:58:57"), dt.datetime(2020, 6, 23, 3, 58, 57))
        self.assertEqual(parse_timestamp("2020-03-20 02:32:49.426"), dt.datetime(2020, 3, 20, 2, 32, 49, 426000))
        self.assertEqual(parse_timestamp("2020-03-20T02:32:49Z"), dt.datetime(2020, 3, 20, 2, 32, 49))
        self.assertEqual(parse_timestamp("2020-03-20 02:00:00+02:00"), dt.datetime(2020, 3, 20, 0, 0))
        self.assertEqual(parse_timestamp("2020-03-20"), dt.datetime(2020, 3, 20))
        for bad in ("2020-02-30 00:00:00", " 2020-03-20", "yesterday", "2020-03-20 25:00:00"):
            with self.assertRaises(SqlError):
                parse_timestamp(bad)

    def test_boolean_and_timestamp_cases(self):
        from fixwitness.sql import generate_sql_cases, read_bundle
        t = {"forms": b"id,is_deleted,deleted_at\n1,FALSE,\n2,FALSE,2020-06-23 3:58:57\n"}
        types = {"forms": {"id": "integer", "is_deleted": "boolean", "deleted_at": "timestamp"}}
        cases = generate_sql_cases(t, types, rows=2, max_cases=500)
        flips = [c for c in cases if c.category == "flip"]
        self.assertEqual([c.value for c in flips], ["true"])  # the other value of the row's FALSE
        edges = {c.value for c in cases if c.category == "time-edge"}
        self.assertTrue({"2020-06-23 00:00:00", "2020-06-23 23:59:59.999999", "2020-06-24 00:00:00",
                         "1970-01-01 00:00:00"} <= edges, edges)
        for c in cases:  # every case can be loaded with the columns' types
            tables, _ = read_bundle(c.content)
            for line in tables["forms"].splitlines()[1:]:
                self.assertNotIn(line.split(",")[1].strip().lower(), ("padded", "ünïcødé"))

    def test_seed_types_from_dbt_are_used(self):
        """A model that needs a real boolean (NOT coalesce(flag, false)) runs, because the seed is
        loaded with the type dbt gave it (on SQLite, as 1 and 0)."""
        from fixwitness.sql import TYPES_FILE, kind_of, run_pipeline, make_bundle, read_outputs
        models = self.tmp / "models"
        write(models / "live.sql", 'select id from "forms" where not coalesce(is_deleted, false)\n')
        write(models / "fixwitness_order.txt", "live\n")
        (models / TYPES_FILE).write_text(json.dumps({"adapter": "duckdb",
                                                     "types": {"forms": {"id": "BIGINT", "is_deleted": "BOOLEAN"}}}))
        tables = {"forms": b"id,is_deleted\n1,FALSE\n2,TRUE\n3,\n"}
        types = {"forms": {"id": "integer", "is_deleted": kind_of("BOOLEAN")}}
        out = read_outputs(run_pipeline(models, make_bundle(tables, types), engine="sqlite"))
        self.assertEqual(out["live"].decode().split(), ["id", "1", "3"])
        if importlib.util.find_spec("duckdb") is not None:
            out = read_outputs(run_pipeline(models, make_bundle(tables, types), engine="duckdb"))
            self.assertEqual(out["live"].decode().split(), ["id", "1", "3"])

    @unittest.skipUnless(importlib.util.find_spec("duckdb"), "needs duckdb")
    def test_quoted_seed_header_gets_dbts_name(self):
        """A seed header written "default" in quotes (for warehouses that need it) is the column
        default when dbt does not quote seed columns: the column gets the name dbt stored."""
        import duckdb
        from fixwitness.sql import load_tables
        con = duckdb.connect()
        load_tables(con, "duckdb", {"brand": 'id,"""default"""\n1,TRUE\n'}, {"brand": {"id": "integer", '"default"': "boolean"}},
                    {"brand": {"id": "BIGINT", "default": "BOOLEAN"}})
        self.assertEqual(con.execute('select "default" from brand').fetchall(), [(True,)])

    def test_dbt_errors_say_why(self):
        from fixwitness.dbtmode import error_lines
        log = ("\x1b[0m06:24:50  Running with dbt=1.10.1\n\x1b[0m06:24:51  Encountered an error:\n"
               "Runtime Error\n  Could not convert string 'abc' to INT32 in seed order_data\n"
               "06:24:51  Done. PASS=0 WARN=0 ERROR=1 SKIP=0 TOTAL=1\n")
        self.assertEqual(error_lines(log)[:3], ["Encountered an error:", "Runtime Error",
                                                "Could not convert string 'abc' to INT32 in seed order_data"])


class SqlModeTests(TempDirTest):
    def _check(self, after_sql: str, before_sql: str = REVENUE, **extra):
        write(self.tmp / "orders.csv", ORDERS)
        write(self.tmp / "customers.csv", CUSTOMERS)
        write(self.tmp / "before.sql", before_sql)
        write(self.tmp / "after.sql", after_sql)
        settings = dict(before=str(self.tmp / "before.sql"), after=str(self.tmp / "after.sql"),
                        tables={"orders": str(self.tmp / "orders.csv"), "customers": str(self.tmp / "customers.csv")},
                        engine="sqlite")
        settings.update(extra)
        return self.check(**settings)

    def test_equivalent_refactor_passes(self):
        proof = self._check("""
            with paid as (select customer_id, amount from orders where status = 'paid')
            select c.region, sum(p.amount) as revenue, count(*) as orders
            from paid p join customers c on c.customer_id = p.customer_id
            group by c.region
        """)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertFalse(proof["security"]["checked"])
        self.assertEqual(proof["config"]["sql"]["engine"], "sqlite")

    def test_count_column_instead_of_count_star_fails_on_nulls(self):
        proof = self._check(REVENUE.replace("count(*)", "count(o.amount)"))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("empty", {d["category"] for d in proof["differences"]})

    def test_left_join_keeps_orders_without_a_customer(self):
        proof = self._check(REVENUE.replace("join customers", "left join customers"))
        self.assertEqual(proof["verdict"], "FAIL")

    def test_dbt_model_with_refs(self):
        model = REVENUE.replace("from orders o", "from {{ ref('orders') }} o") \
                       .replace("join customers c", "join {{ ref('customers') }} c")
        proof = self._check("{{ config(materialized='table') }}\n" + model)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])

    def test_incident_table_and_replay(self):
        write(self.tmp / "orders_new.csv", ORDERS.replace("amount", "amount_usd"))
        proof = self._check(REVENUE.replace("o.amount", "o.amount_usd"),
                            incident_tables={"orders": str(self.tmp / "orders_new.csv")})
        self.assertEqual(proof["incident"]["status"], "resolved")
        self.assertEqual(proof["verdict"], "FAIL")  # the fix no longer works on the old column name
        from fixwitness.report import write_outputs
        path = write_outputs(proof, self.tmp / "out")
        result = replay(json.loads(path.read_text()))
        self.assertTrue(result["reproduced"], result["problems"])

    @unittest.skipUnless(importlib.util.find_spec("duckdb"), "DuckDB not installed")
    def test_duckdb_engine(self):
        ok = self._check(REVENUE.replace("count(*)", "count(1)"), engine="duckdb")
        self.assertEqual(ok["config"]["sql"]["engine"], "duckdb")
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        bad = self._check(REVENUE.replace("count(*)", "count(o.amount)"), engine="duckdb")
        self.assertEqual(bad["verdict"], "FAIL")


STG_ORDERS = "select order_id, customer_id, amount from {{ ref('orders') }} where status = 'paid'\n"
STG_CUSTOMERS = "select customer_id, region from customers\n"
PIPE_REVENUE = """
    -- final model: revenue per region
    select c.region, sum(o.amount) as revenue, count(*) as orders
    from {{ ref('stg_orders') }} o
    join stg_customers c on c.customer_id = o.customer_id
    group by c.region
"""


class ReportTests(TempDirTest):
    """Plain-English findings, the smallest input that shows them, and report.html."""
    _check = SqlModeTests._check

    def test_finding_is_explained_shrunk_and_rendered(self):
        from fixwitness.report import write_outputs
        proof = self._check(REVENUE.replace("count(*)", "count(o.amount)"))
        self.assertEqual(proof["verdict"], "FAIL")
        d = next(x for x in proof["differences"] if x["category"] == "empty" and x["column"] == "orders.amount")
        self.assertEqual(d["impact"], "numbers")
        self.assertTrue(d["explanation"].startswith("If an `orders` row has an empty `amount`, `orders` for 'east'"),
                        d["explanation"])
        self.assertTrue(d["shrunk"])
        out = write_outputs(proof, self.tmp / "out").parent
        repro = out / "repro" / d["id"] / "tables" / "orders.csv"
        self.assertEqual(len(repro.read_text().strip().splitlines()), 2, repro.read_text())  # header + one row
        page = (out / "report.html").read_text()
        self.assertIn("Don&#x27;t merge yet", page)
        self.assertIn("Numbers change", page)
        self.assertIn('class="m"', page)  # the changed input cell is marked
        self.assertIn("**Numbers change.** If an `orders` row", (out / "report.md").read_text())

    def test_pass_and_no_shrink(self):
        from fixwitness.report import write_outputs
        ok = self._check(REVENUE.replace("count(*) as orders", "count(1) as orders"))
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        page = (write_outputs(ok, self.tmp / "ok").parent / "report.html").read_text()
        self.assertIn("Safe to merge", page)
        bad = self._check(REVENUE.replace("count(*)", "count(o.amount)"), shrink=False)
        self.assertFalse(any(x["shrunk"] for x in bad["differences"]))

    def test_sentences(self):
        from fixwitness.explain import align, input_phrase
        self.assertEqual(input_phrase("missing-key", "status", "<key left out>", False), "a record has no `status` key")
        self.assertEqual(input_phrase("duplicate-row", "orders", None, True), "an `orders` row appears twice")
        view = align((["region", "n"], [["east", "2"], ["west", "1"]]), (["region", "n"], [["east", "2"]]))
        self.assertEqual([r["state"] for r in view["rows"]], ["both", "original"])
        view = align((["k", "v"], [["a", "1.0"]]), (["k", "v"], [["a", "1"]]))
        self.assertFalse(view["rows"][0]["cells"][1]["changed"])


class PairsAndFocusTests(unittest.TestCase):
    def test_pairs_put_two_rows_of_one_group_together(self):
        cases = generate_cases(ORDERS.encode(), attacks=False)
        pairs = [c for c in cases if c.category == "pairs" and c.column == "amount"]
        self.assertEqual({c.value for c in pairs}, {"0.005 | 0.005", "2.675 | 1.005", "0.1 | 0.2", "-0.5 | 0.5",
                                                    "9007199254740993 | 1"})
        rows = [r.split(",") for r in pairs[1].content.decode().strip().splitlines()[1:]]
        self.assertEqual(len(rows), 4)  # the twin sits next to its row, with the same group columns
        self.assertEqual(rows[1][:2], rows[2][:2])
        reviewed = generate_cases(ORDERS.encode(), attacks=False, review=["duplicate-row"])
        kinds = {c.value: c.kind for c in reviewed if c.category == "pairs" and c.column == "amount"}
        self.assertEqual((kinds["0.005 | 0.005"], kinds["2.675 | 1.005"]), ("review", "valid"))
        reviewed = generate_cases(ORDERS.encode(), attacks=False, review=["duplicate"])  # the twin repeats keys
        self.assertTrue(all(c.kind == "review" for c in reviewed if c.category == "pairs"))

    def test_focus_keeps_the_touched_columns_under_the_cap(self):
        from fixwitness.cases import focus_columns
        before, after = "select count(*) from orders", "select count(amount) from orders"
        self.assertEqual(focus_columns(before, after, ["order_id", "amount", "status"]), ["amount"])
        self.assertEqual(focus_columns(before, after, ["orders.amount", "orders.status"]), ["orders.amount"])
        full = sum(c.column == "amount" for c in generate_cases(ORDERS.encode(), attacks=False))
        focused = generate_cases(ORDERS.encode(), max_cases=120, attacks=False, focus=["amount"])
        plain = generate_cases(ORDERS.encode(), max_cases=120, attacks=False)
        self.assertEqual(sum(c.column == "amount" for c in focused), full)  # every case of the touched column
        self.assertLess(sum(c.column == "amount" for c in plain), full)


class PipelineUnitTests(unittest.TestCase):
    def test_run_order_and_dependencies(self):
        from fixwitness.sql import SqlError, dependencies, run_order
        models = {"revenue": PIPE_REVENUE, "stg_orders": STG_ORDERS, "stg_customers": STG_CUSTOMERS}
        names = set(models) | {"orders", "customers"}
        self.assertEqual(dependencies(PIPE_REVENUE, names, "revenue"), {"stg_orders", "stg_customers"})
        self.assertEqual(dependencies("select 'from stg_orders' as x -- join revenue\nfrom orders", names, "x"),
                         {"orders"})
        self.assertEqual(run_order(models)[-1], "revenue")
        with self.assertRaises(SqlError):
            run_order({"a": "select * from b", "b": "select * from a"})

    def test_named_outputs_compare_per_model(self):
        from fixwitness.compare import CompareOptions, compare, unstable_columns
        from fixwitness.sql import make_outputs
        a = make_outputs({"m1": b"x,y\n1,2\n", "m2": b"k\n1\n"})
        b = make_outputs({"m1": b"x,y\n1,3\n", "m2": b"k\n1\n"})
        st, det = compare(a, b, CompareOptions())
        self.assertEqual(st, "changed")
        self.assertTrue(det and all(d.startswith("m1: ") for d in det), det)
        self.assertEqual(compare(a, b, CompareOptions(ignore_columns={"m1.y"}))[0], "same-data")
        self.assertEqual(compare(a, make_outputs({"m1": b"x,y\n1,2\n"}), CompareOptions())[1],
                         ["m2: only in the original's output"])
        self.assertEqual(unstable_columns(a, b), ({"m1.y"}, None))


class PipelineModeTests(TempDirTest):
    def _models(self, name: str, models: dict[str, str]) -> Path:
        for model, sql in models.items():
            write(self.tmp / name / model, sql)
        return self.tmp / name

    def _check(self, after: dict[str, str], **extra):
        write(self.tmp / "orders.csv", ORDERS)
        write(self.tmp / "customers.csv", CUSTOMERS)
        before = self._models("before", {"staging/stg_orders.sql": STG_ORDERS,
                                         "staging/stg_customers.sql": STG_CUSTOMERS,
                                         "marts/revenue.sql": PIPE_REVENUE})
        settings = dict(before=str(before), after=str(self._models("after", after)), engine="sqlite",
                        tables={"orders": str(self.tmp / "orders.csv"), "customers": str(self.tmp / "customers.csv")})
        settings.update(extra)
        return self.check(**settings)

    def test_refactor_that_splits_a_model_passes(self):
        proof = self._check({"staging/stg_orders.sql": STG_ORDERS.replace("amount from", "amount, status from")
                                                                 .replace("where status = 'paid'", ""),
                             "staging/paid_orders.sql": "select order_id, customer_id, amount from stg_orders "
                                                        "where status = 'paid'\n",
                             "staging/stg_customers.sql": STG_CUSTOMERS,
                             "marts/revenue.sql": PIPE_REVENUE.replace("ref('stg_orders')", "ref('paid_orders')")})
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertEqual(proof["config"]["sql"]["outputs"], ["revenue"])

    def test_staging_change_is_caught_in_the_final_model(self):
        proof = self._check({"staging/stg_orders.sql": STG_ORDERS.replace("status = 'paid'", "status <> 'refunded'"),
                             "staging/stg_customers.sql": STG_CUSTOMERS, "marts/revenue.sql": PIPE_REVENUE})
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertTrue(all(d.startswith("revenue: ") for x in proof["differences"] for d in x["details"]),
                        proof["differences"][:2])

    def test_all_outputs_reports_a_removed_model(self):
        proof = self._check({"staging/orders_paid.sql": STG_ORDERS,
                             "staging/stg_customers.sql": STG_CUSTOMERS,
                             "marts/revenue.sql": PIPE_REVENUE.replace("ref('stg_orders')", "ref('orders_paid')")},
                            sql_outputs=["all"])
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("stg_orders: only in the original's output", proof["differences"][0]["details"])

    def test_git_mode_on_a_models_folder_and_replay(self):
        repo = self.repo({"models/stg_orders.sql": STG_ORDERS, "models/stg_customers.sql": STG_CUSTOMERS,
                          "models/revenue.sql": PIPE_REVENUE, "data/orders.csv": ORDERS,
                          "data/customers.csv": CUSTOMERS})
        write(repo / "models/stg_orders.sql", STG_ORDERS.replace("select order_id,", "select distinct order_id,"))
        os.chdir(repo)
        proof = self.check(path="models", engine="sqlite",
                           tables={"orders": "data/orders.csv", "customers": "data/customers.csv"})
        self.assertEqual(proof["verdict"], "FAIL")  # DISTINCT drops a repeated order row
        self.assertIn("duplicate-row", {d["category"] for d in proof["differences"]})
        from fixwitness.report import write_outputs
        result = replay(json.loads(write_outputs(proof, self.tmp / "out").read_text()))
        self.assertTrue(result["reproduced"], result["problems"])

    def test_expected_output_for_one_final_model(self):
        write(self.tmp / "orders_new.csv", ORDERS.replace("paid", "PAID"))
        write(self.tmp / "expected.csv", "region,revenue,orders\neast,318.5,3\n")
        proof = self._check({"staging/stg_orders.sql": STG_ORDERS.replace("status = 'paid'", "lower(status) = 'paid'"),
                             "staging/stg_customers.sql": STG_CUSTOMERS, "marts/revenue.sql": PIPE_REVENUE},
                            incident_tables={"orders": str(self.tmp / "orders_new.csv")},
                            incident_expected=str(self.tmp / "expected.csv"), review=["case"])
        self.assertEqual(proof["incident"]["status"], "resolved", proof.get("incident_details"))
        self.assertIn("expected output", proof["incident"]["checks"])


PD_REVENUE = """
    import pandas as pd

    def revenue(orders, customers):
        paid = orders[orders["status"] == "paid"]
        joined = paid.merge(customers, on="customer_id")
        return joined.groupby("region").agg(revenue=("amount", "sum"), orders=("order_id", "size"))
"""
HAS = {m: importlib.util.find_spec(m) is not None for m in ("pandas", "polars", "pyspark")}


@unittest.skipUnless(HAS["pandas"], "pandas not installed")
class FrameUnitTests(unittest.TestCase):
    def test_results_become_csv(self):
        import pandas as pd
        from fixwitness.pyrun import to_csv
        from fixwitness.sql import read_outputs
        df = pd.DataFrame({"region": ["west", "east"], "n": [1, None]})
        self.assertEqual(to_csv(df, False), b"region,n\neast,\nwest,1.0\n")      # unnamed index dropped
        self.assertEqual(to_csv(df.set_index("region")["n"], True), b"region,n\nwest,1.0\neast,\n")
        self.assertEqual(to_csv(3, False), b"value\n3\n")
        named = read_outputs(to_csv({"a": df, "b": df.head(1)}, False))
        self.assertEqual(sorted(named), ["a", "b"])
        self.assertEqual(to_csv(pd.DataFrame({"d": pd.to_datetime(["2024-01-02"])}), False), b"d\n2024-01-02\n")

    def test_library_and_arguments(self):
        from fixwitness.pyrun import FrameError, arguments, detect_library
        self.assertEqual(detect_library("import polars as pl\n"), "polars")
        self.assertEqual(detect_library("from pyspark.sql import functions as F\n"), "pyspark")
        self.assertEqual(detect_library("# import polars\nimport pandas\n"), "pandas")
        self.assertEqual(arguments(lambda orders, customers, top=3: 0, ["customers", "orders"]),
                         ([], ["orders", "customers"]))
        self.assertEqual(arguments(lambda df: 0, ["orders"]), (["orders"], []))
        with self.assertRaises(FrameError):
            arguments(lambda a, b: 0, ["orders", "customers"])


@unittest.skipUnless(HAS["pandas"], "pandas not installed")
class FrameModeTests(TempDirTest):
    def _check(self, after: str, before: str = PD_REVENUE, **extra):
        write(self.tmp / "orders.csv", ORDERS)
        write(self.tmp / "customers.csv", CUSTOMERS)
        write(self.tmp / "before.py", before)
        write(self.tmp / "after.py", after)
        settings = dict(before=str(self.tmp / "before.py"), after=str(self.tmp / "after.py"), function="revenue",
                        tables={"orders": str(self.tmp / "orders.csv"), "customers": str(self.tmp / "customers.csv")},
                        max_cases=80)  # about half a second per run: keep the suite quick
        settings.update(extra)
        return self.check(**settings)

    def test_equivalent_refactor_passes(self):
        proof = self._check("""
            def revenue(orders, customers):
                joined = customers.merge(orders.query("status == 'paid'"), on="customer_id", how="inner")
                out = joined.groupby("region")[["amount"]].sum().rename(columns={"amount": "revenue"})
                out["orders"] = joined.groupby("region").size()
                return out
        """)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertEqual(proof["config"]["frame"]["libraries"], ["pandas", "pandas"])
        self.assertFalse(proof["security"]["checked"])

    def test_count_of_a_column_with_missing_values_fails(self):
        proof = self._check(PD_REVENUE.replace('("order_id", "size")', '("amount", "count")'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("empty", {d["category"] for d in proof["differences"]})

    def test_drop_duplicates_fails_on_a_repeated_row(self):
        proof = self._check(PD_REVENUE.replace('orders["status"] == "paid"]', 'orders["status"] == "paid"].drop_duplicates()'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("duplicate-row", {d["category"] for d in proof["differences"]})

    def test_case_insensitive_match_fails(self):
        proof = self._check(PD_REVENUE.replace('orders["status"] == "paid"', 'orders["status"].str.lower() == "paid"'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("case", {d["category"] for d in proof["differences"]})

    def test_git_mode_and_replay(self):
        repo = self.repo({"etl/revenue.py": PD_REVENUE, "data/orders.csv": ORDERS, "data/customers.csv": CUSTOMERS})
        write(repo / "etl/revenue.py", PD_REVENUE.replace('paid.merge(customers, on="customer_id")',
                                                          'pd.merge(paid, customers, on="customer_id")'))
        os.chdir(repo)
        proof = self.check(path="etl/revenue.py", function="revenue", max_cases=40,
                           tables={"orders": "data/orders.csv", "customers": "data/customers.csv"})
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        from fixwitness.report import write_outputs
        result = replay(json.loads(write_outputs(proof, self.tmp / "out").read_text()))
        self.assertTrue(result["reproduced"], result["problems"])

    def test_warm_server_gives_the_same_results_as_separate_processes(self):
        wrong = PD_REVENUE.replace('("order_id", "size")', '("amount", "count")')
        fast = self._check(wrong, max_cases=40)
        os.environ["FIXWITNESS_NO_SERVER"] = "1"
        try:
            slow = self._check(wrong, max_cases=40)
        finally:
            del os.environ["FIXWITNESS_NO_SERVER"]
        self.assertEqual([(c["id"], c["status"]) for c in fast["cases"]], [(c["id"], c["status"]) for c in slow["cases"]])
        self.assertFalse(any("own process" in w for w in fast["warnings"]), fast["warnings"])

    def test_warm_server_enforces_the_timeout(self):
        t0 = time.time()
        proof = self._check(PD_REVENUE.replace("    paid = ", "    __import__('time').sleep(60)\n    paid = "),
                            max_cases=10, timeout=2)
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertLess(time.time() - t0, 90)  # 10 cases x 2 s, not 10 x 60 s

    @unittest.skipUnless(HAS["polars"], "polars not installed")
    def test_pandas_to_polars_migration(self):
        # A faithful rewrite: null keys match in the join and the null group is dropped, as in pandas.
        polars_ok = """
            import polars as pl

            def revenue(orders, customers):
                return (orders.filter(pl.col("status") == "paid")
                        .join(customers, on="customer_id", how="inner", nulls_equal=True)
                        .group_by("region").agg(pl.col("amount").sum().alias("revenue"), pl.len().alias("orders"))
                        .drop_nulls("region"))
        """
        proof = self._check(polars_ok)
        self.assertEqual(proof["config"]["frame"]["libraries"], ["pandas", "polars"])
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        bad = self._check(polars_ok.replace('pl.len()', 'pl.col("amount").count()'))
        self.assertEqual(bad["verdict"], "FAIL")
        null_group = self._check(polars_ok.replace('\n                        .drop_nulls("region"))', ')'))
        self.assertEqual(null_group["verdict"], "FAIL")  # polars keeps the null group that pandas drops

    @unittest.skipUnless(HAS["pyspark"], "pyspark not installed")
    def test_pyspark_function(self):
        spark = """
            from pyspark.sql import functions as F

            def revenue(orders, customers):
                # as pandas: null keys match, the null group is dropped, an all-null sum is 0
                c = customers.withColumnRenamed("customer_id", "cid")
                joined = orders.where(F.col("status") == "paid").join(c, F.col("customer_id").eqNullSafe(F.col("cid")))
                return (joined.where(F.col("region").isNotNull()).groupBy("region")
                        .agg(F.coalesce(F.sum("amount"), F.lit(0.0)).alias("revenue"), F.count("*").alias("orders")))
        """
        proof = self._check(spark, max_cases=40, timeout=120)
        self.assertEqual(proof["config"]["frame"]["libraries"], ["pandas", "pyspark"])
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])


EVENTS = (
    '{"id": 1, "user": {"id": "u1", "country": "US"}, "amount": 12.5, "status": "paid", "tags": ["a", "b"]}\n'
    '{"id": 2, "user": {"id": "u2", "country": "DE"}, "amount": 300.75, "status": "paid", "tags": []}\n'
    '{"id": 3, "user": {"id": "u3", "country": "US"}, "amount": 99.99, "status": "refunded", "tags": ["c"]}\n'
)
EVENTS_TOTALS = """
    import json, sys
    totals = {}
    with open(sys.argv[1]) as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("status") != "paid":
                continue
            c = e["user"]["country"]
            totals[c] = totals.get(c, 0) + e["amount"]
    with open(sys.argv[2], "w") as out:
        for c in sorted(totals):
            out.write(json.dumps({"country": c, "revenue": round(totals[c], 2)}) + "\\n")
"""


class JsonUnitTests(unittest.TestCase):
    def test_cases_cover_json_paths_and_literals(self):
        from fixwitness.formats import generate_json_cases
        cases = generate_json_cases(EVENTS.encode(), attacks=False)
        by_col = {}
        for c in cases:
            by_col.setdefault(c.column, set()).add(c.category)
        self.assertTrue({"missing-key", "null", "numeric-format", "json-type"} <= by_col["amount"])
        self.assertTrue({"missing-key", "case", "unicode"} <= by_col["user.country"])
        self.assertIn("array", by_col["tags"])
        self.assertIn("schema", by_col[None])
        literal = next(c for c in cases if c.column == "amount" and c.value == "1e3")
        self.assertIn(b'"amount": 1e3', literal.content)
        missing = next(c for c in cases if c.column == "user.country" and c.category == "missing-key")
        self.assertIn(b'"user": {"id": "u2"}', missing.content)

    def test_wrapped_array_keeps_its_wrapper(self):
        from fixwitness.formats import generate_json_cases, parse_json_sample
        sample = json.dumps({"meta": {"page": 1}, "data": [{"a": 1}, {"a": 2}]}).encode()
        for c in generate_json_cases(sample, attacks=False):
            if c.value == "<no records>":
                self.assertEqual(json.loads(c.content), {"meta": {"page": 1}, "data": []})
            elif c.category not in ("file-structure",):
                self.assertEqual(json.loads(c.content)["meta"], {"page": 1})
        from fixwitness.cases import SampleError
        with self.assertRaises(SampleError):
            parse_json_sample(b'{"a": [{"x": 1}], "b": [{"y": 2}]}')

    def test_json_outputs_compare_by_value(self):
        from fixwitness.compare import CompareOptions, compare
        opts = CompareOptions(mode="json")
        self.assertEqual(compare(b'{"a": 1, "b": [1, 2]}', b'{"b": [1, 2], "a": 1.0}', opts)[0], "same-data")
        st, det = compare(b'{"a": 1, "b": {"c": "x"}}\n', b'{"a": 1, "b": {"c": "y"}}\n', opts)
        self.assertEqual((st, det), ("changed", ['b.c: "x" -> "y"']))
        self.assertEqual(compare(b'{"a": true}', b'{"a": 1}', opts)[0], "changed")
        self.assertEqual(compare(b'[{"a": 1}, {"a": 2}]', b'[{"a": 2}, {"a": 1}]',
                                 CompareOptions(mode="json", unordered=True))[0], "same-data")
        self.assertEqual(compare(b'{"t": 1, "v": 2}', b'{"t": 5, "v": 2}',
                                 CompareOptions(mode="json", ignore_columns={"t"}))[0], "same-data")


class JsonModeTests(TempDirTest):
    def _check(self, after: str, before: str = EVENTS_TOTALS, **extra):
        write(self.tmp / "events.jsonl", EVENTS)
        write(self.tmp / "before.py", before)
        write(self.tmp / "after.py", after)
        settings = dict(before=str(self.tmp / "before.py"), after=str(self.tmp / "after.py"),
                        sample=str(self.tmp / "events.jsonl"), attacks=False)
        settings.update(extra)
        return self.check(**settings)

    def test_equivalent_refactor_passes(self):
        proof = self._check("""
            import json, sys
            from collections import defaultdict

            def main(src, dst):
                totals = defaultdict(int)
                with open(src) as f:
                    for e in (json.loads(l) for l in f if l.strip()):
                        if e.get("status") == "paid":
                            totals[e["user"]["country"]] += e["amount"]
                with open(dst, "w") as out:
                    out.writelines(json.dumps({"country": c, "revenue": round(v, 2)}) + "\\n"
                                   for c, v in sorted(totals.items()))

            main(*sys.argv[1:3])
        """)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertEqual(proof["config"]["output"], "json")

    def test_strict_key_access_fails_on_a_missing_key(self):
        proof = self._check(EVENTS_TOTALS.replace('e.get("status")', 'e["status"]'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn(("missing-key", "status"), {(d["category"], d["column"]) for d in proof["differences"]})

    def test_float_conversion_fails_on_a_large_integer(self):
        proof = self._check(EVENTS_TOTALS.replace('+ e["amount"]', '+ float(e["amount"])'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("numeric-format", {d["category"] for d in proof["differences"]})

    def test_a_changing_timestamp_key_is_ignored(self):
        stamped = EVENTS_TOTALS.replace('"revenue": round(totals[c], 2)}',
                                        '"revenue": round(totals[c], 2), "run_at": __import__("time").time_ns()}')
        proof = self._check(stamped, before=stamped)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])
        self.assertIn("run_at", proof["config"]["auto_ignored_columns"])


SNOWFLAKE_REVENUE = """
    select c.region, sum(iff(o.status = 'paid', o.amount, 0)) as revenue, count(*) as orders
    from analytics.raw.orders o
    join analytics.raw.customers c on c.customer_id = o.customer_id
    group by c.region
"""


@unittest.skipUnless(importlib.util.find_spec("sqlglot"), "sqlglot not installed")
class DialectTests(TempDirTest):
    _check = SqlModeTests._check

    def test_translate_reduces_qualified_names(self):
        from fixwitness.sql import translate
        out = translate("select * from analytics.raw.ORDERS o join `p.d.customers` c using (customer_id)",
                        "bigquery", "duckdb", {"orders", "customers"})
        self.assertNotIn("analytics", out)
        self.assertNotIn("p.d", out)
        self.assertIn("orders", out.lower())

    def test_snowflake_refactor_passes_and_ilike_fails(self):
        ok = self._check("""
            select c.region,
                   sum(case when o.status = 'paid' then o.amount else 0 end) as revenue,
                   count(*) as orders
            from raw.orders as o
            inner join raw.customers as c on o.customer_id = c.customer_id
            group by 1
        """, before_sql=SNOWFLAKE_REVENUE, dialect="snowflake")
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        self.assertEqual(ok["config"]["sql"]["dialect"], "snowflake")
        bad = self._check(SNOWFLAKE_REVENUE.replace("o.status = 'paid'", "o.status ilike 'paid'"),
                          before_sql=SNOWFLAKE_REVENUE, dialect="snowflake")
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertIn("case", {d["category"] for d in bad["differences"]})

    def test_bigquery_safe_divide(self):
        before = """
            select c.region, safe_divide(sum(o.amount), countif(o.status = 'paid')) as avg_paid
            from `shop.sales.orders` o join `shop.sales.customers` c using (customer_id)
            group by c.region
        """
        ok = self._check(before.replace("safe_divide(sum(o.amount), countif(o.status = 'paid'))",
                                        "sum(o.amount) / nullif(countif(o.status = 'paid'), 0)"),
                         before_sql=before, dialect="bigquery")
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])

    def test_unknown_dialect_is_refused(self):
        with self.assertRaises(PlanError):
            self._check(REVENUE, dialect="nosuchsql")


PARQUET_FILTER = """
    import sys
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    t = pq.read_table(sys.argv[1])
    paid = t.filter(pc.equal(t["status"], "paid"))
    pq.write_table(paid.select(["order_id", "amount"]), sys.argv[2])
"""


@unittest.skipUnless(importlib.util.find_spec("pyarrow"), "pyarrow not installed")
class ParquetTests(TempDirTest):
    def _check(self, after: str, **extra):
        import datetime
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.table({"order_id": pa.array([1, 2, 3, 4], pa.int64()),
                          "amount": pa.array([12.5, 300.75, 99.99, 5.25], pa.float64()),
                          "status": pa.array(["paid", "paid", "refunded", "paid"], pa.string()),
                          "day": pa.array([datetime.date(2026, 1, d) for d in (3, 4, 5, 6)], pa.date32())})
        pq.write_table(table, self.tmp / "orders.parquet")
        write(self.tmp / "before.py", PARQUET_FILTER)
        write(self.tmp / "after.py", after)
        settings = dict(before=str(self.tmp / "before.py"), after=str(self.tmp / "after.py"),
                        sample=str(self.tmp / "orders.parquet"), attacks=False)
        settings.update(extra)
        return self.check(**settings)

    def test_cases_keep_the_schema(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        from fixwitness.formats import generate_parquet_cases
        self._check(PARQUET_FILTER)  # writes the sample
        sample = (self.tmp / "orders.parquet").read_bytes()
        cases = generate_parquet_cases(sample)
        self.assertGreater(len(cases), 20)
        schema = pq.read_table(pa.BufferReader(sample)).schema
        for c in cases:  # every column of the sample keeps its type (schema cases add or move columns)
            got = pq.read_table(pa.BufferReader(c.content)).schema
            for field in schema:
                self.assertEqual(got.field(field.name).type, field.type, c.value)
        self.assertIn("null-column", {c.category for c in cases})

    def test_rewrite_in_python_passes(self):
        proof = self._check("""
            import sys
            import pyarrow as pa
            import pyarrow.parquet as pq

            rows = [r for r in pq.read_table(sys.argv[1]).to_pylist() if r["status"] == "paid"]
            out = pa.Table.from_pylist([{"order_id": r["order_id"], "amount": r["amount"]} for r in rows],
                                       schema=pa.schema([("order_id", pa.int64()), ("amount", pa.float64())]))
            pq.write_table(out, sys.argv[2])
        """)
        self.assertEqual(proof["verdict"], "PASS", proof["reasons"])

    def test_case_insensitive_filter_fails(self):
        proof = self._check(PARQUET_FILTER.replace('pc.equal(t["status"], "paid")',
                                                   'pc.equal(pc.utf8_lower(t["status"]), "paid")'))
        self.assertEqual(proof["verdict"], "FAIL")
        self.assertIn("case", {d["category"] for d in proof["differences"]})


class WholeChangeTests(TempDirTest):
    """`fixwitness check` with no file: every changed file, each checked the way that fits it."""

    def _repo(self):
        from pathlib import Path as P
        b = ROOT / "benchmark" / "complex"
        files = {"data/orders.csv": ORDERS, "data/customers.csv": CUSTOMERS,
                 "data/events.jsonl": (b / "C05-jsonl-events" / "events.jsonl").read_text(),
                 "sql/revenue.sql": REVENUE, "jobs/events.py": (b / "C05-jsonl-events" / "original.py").read_text(),
                 "README.md": "# readme\n"}
        if HAS["pandas"]:
            files["etl/revenue.py"] = textwrap.dedent(PD_REVENUE).lstrip()
        repo = self.repo(files)
        P(repo / "sql/revenue.sql").write_text(REVENUE.replace("count(*)", "count(o.amount)"))
        jobs = repo / "jobs/events.py"
        jobs.write_text(jobs.read_text().replace('e.get("status")', 'e["status"]'))
        if HAS["pandas"]:
            etl = repo / "etl/revenue.py"
            etl.write_text(etl.read_text().replace('("order_id", "size")', '("amount", "count")'))
        (repo / "README.md").write_text("# readme, edited\n")
        os.chdir(repo)
        return repo

    def test_items_are_classified_and_tables_found_by_name(self):
        from fixwitness.changes import plan_items
        self._repo()
        items, skipped = plan_items(load_config(None, {}))
        kinds = {i.target: i.kind for i in items}
        self.assertEqual(kinds["sql/revenue.sql"], "sql")
        self.assertEqual(kinds["jobs/events.py"], "script")
        if HAS["pandas"]:
            self.assertEqual(kinds["etl/revenue.py: revenue()"], "dataframe")
        self.assertIn(("README.md", "not code"), skipped)

    def test_every_change_is_checked_with_one_verdict(self):
        from fixwitness.changes import plan_items, run_items
        repo = self._repo()
        cfg = load_config(None, {"engine": "sqlite", "max_cases": 60, "attacks": False})
        items, _ = plan_items(cfg)
        result = run_items(cfg, items, repo / ".fixwitness")
        self.assertEqual(result["verdict"], "FAIL")
        verdicts = {r["target"]: r["verdict"] for r in result["checks"]}
        self.assertEqual(verdicts["sql/revenue.sql"], "FAIL")
        self.assertEqual(verdicts["jobs/events.py"], "FAIL")  # the sample is events.jsonl: the script reads JSON
        if HAS["pandas"]:
            self.assertEqual(verdicts["etl/revenue.py: revenue()"], "FAIL")
        # every difference comes with a reproduction: the input, both outputs, the commands
        sql = next(r for r in result["checks"] if r["target"] == "sql/revenue.sql")
        repro = Path(sql["proof"]).parent / "repro"
        cases = sorted(repro.iterdir())
        self.assertTrue(cases)
        names = {p.name for p in cases[0].iterdir()}
        self.assertTrue({"README.md", "input.json", "original.csv", "fix.csv", "tables"} <= names, names)
        self.assertIn("git worktree add", (cases[0] / "README.md").read_text())

    def test_mcp_prove_change(self):
        from fixwitness.mcp_server import handle
        self._repo()
        reply = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "prove_change", "arguments": {"attacks": False, "max_cases": 30,
                                                                          "engine": "sqlite"}}})
        result = reply["result"]["structuredContent"]
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("sql/revenue.sql", {c["target"] for c in result["checks"]})
        self.assertIn({"path": "README.md", "why": "not code"}, result["not_checked"])

    def test_accept_marks_a_difference_as_intended(self):
        repo = self._repo()
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        r = subprocess.run([sys.executable, "-m", "fixwitness", "accept", "--target", "jobs/events.py",
                            "--category", "missing-key", "--column", "status", "--note", "status is required now"],
                           capture_output=True, text=True, env=env, cwd=repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('category = "missing-key"', (repo / "fixwitness.toml").read_text())
        r = subprocess.run([sys.executable, "-m", "fixwitness", "check", "jobs/events.py", "--no-attacks",
                            "--max-cases", "60"], capture_output=True, text=True, env=env, cwd=repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("marked as intended", r.stdout)

    def test_ui_server(self):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from fixwitness.ui import Handler, State
        repo = self._repo()
        state = State(repo)
        server = ThreadingHTTPServer(("127.0.0.1", 0), type("H", (Handler,), {"state": state}))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with self.assertRaises(urllib.error.HTTPError):  # no token, no access
                urllib.request.urlopen(base + "/api/plan")
            plan = json.load(urllib.request.urlopen(f"{base}/api/plan?t={state.token}"))
            self.assertIn("sql/revenue.sql", [i["target"] for i in plan["items"]])
            req = urllib.request.Request(base + "/api/accept", method="POST",
                                         data=json.dumps({"category": "case", "column": "orders.status"}).encode(),
                                         headers={"X-Fixwitness-Token": state.token})
            self.assertEqual(json.load(urllib.request.urlopen(req))["accepted"]["category"], "case")
            self.assertIn("[[accept]]", (repo / "fixwitness.toml").read_text())
        finally:
            server.shutdown()
            server.server_close()

    def test_adapter_claims_a_new_kind_of_file(self):
        from fixwitness.changes import plan_items, run_items
        repo = self._repo()
        write(repo / "jobs" / "clean.etl", "import csv, sys\nrows = list(csv.reader(open(sys.argv[1])))\n"
              "csv.writer(open(sys.argv[2], 'w', newline='')).writerows(rows)\n")
        write(repo / "tools" / "fw_adapters.py", textwrap.dedent("""
            class EtlJob:
                name = "etl job"
                def claims(self, path, root):
                    return path.suffix == ".etl"
                def settings(self, path, root):
                    return {"run": "python3 {script} {input} {output}", "sample": "data/orders.csv",
                            "attacks": False, "allow_any_command": True}
        """))
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "etl job")
        write(repo / "jobs" / "clean.etl", (repo / "jobs" / "clean.etl").read_text().replace(
            "writerows(rows)", "writerows(r for r in rows if r[2] != '')"))
        os.environ["FIXWITNESS_ADAPTERS"] = "tools/fw_adapters.py:EtlJob"
        try:
            cfg = load_config(None, {})
            items, _ = plan_items(cfg)
            item = next(i for i in items if i.target == "jobs/clean.etl")
            self.assertEqual(item.kind, "etl job")
            self.assertNotIn("allow_any_command", item.overrides)
            result = run_items(cfg, [item])
            self.assertEqual(result["checks"][0]["verdict"], "FAIL")  # rows with an empty amount are dropped
        finally:
            del os.environ["FIXWITNESS_ADAPTERS"]

    def test_proofs_match_the_published_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        from fixwitness.report import write_outputs
        schema = json.loads((ROOT / "docs" / "proof.schema.json").read_text())
        repo = self._repo()
        proof = self.check(path="sql/revenue.sql", engine="sqlite", max_cases=30,
                           tables={"orders": "data/orders.csv", "customers": "data/customers.csv"})
        record = json.loads(write_outputs(proof, repo / "out").read_text())
        jsonschema.validate(record, schema)
        self.assertTrue(record["$schema"].endswith("docs/proof.schema.json"))

    def test_cli_with_no_file(self):
        self._repo()
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        r = subprocess.run([sys.executable, "-m", "fixwitness", "check", "--dry-run"], capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("sql/revenue.sql", r.stdout)
        self.assertIn("README.md: not code", r.stdout)


class DbtManifestTests(TempDirTest):
    """A dbt project checked from manifests (what dbt compile writes): relation names, the graph,
    seeds as tables, and the published models downstream of the change."""

    def _manifests(self):
        R = lambda n: f'"memory"."main"."{n}"'  # noqa: E731

        def node(kind, name, code=None, deps=(), mat="table", path=None):
            n = {"resource_type": kind, "name": name, "package_name": "shop", "language": "sql",
                 "original_file_path": path or f"models/{name}.sql", "relation_name": R(name),
                 "config": {"materialized": mat}, "depends_on": {"nodes": list(deps)}}
            if code is not None:
                n["compiled_code"] = code
            return n

        def manifest(stg, rev):
            return {"metadata": {"adapter_type": "duckdb", "project_name": "shop"}, "sources": {}, "nodes": {
                "seed.shop.raw_orders": node("seed", "raw_orders", path="seeds/raw_orders.csv"),
                "seed.shop.raw_customers": node("seed", "raw_customers", path="seeds/raw_customers.csv"),
                "model.shop.stg_orders": node("model", "stg_orders", stg, ["seed.shop.raw_orders"], "view"),
                "model.shop.paid": node("model", "paid", None, ["model.shop.stg_orders"], "ephemeral"),
                "model.shop.stg_customers": node("model", "stg_customers",
                                                 f"select customer_id, region from {R('raw_customers')}",
                                                 ["seed.shop.raw_customers"]),
                "model.shop.revenue": node("model", "revenue", rev, ["model.shop.paid", "model.shop.stg_customers"])}}

        stg = f"select order_id, customer_id, amount, status from {R('raw_orders')}"
        # The CTE `orders` has the name of a column: dbt's graph, not the SQL, gives the order.
        rev = (f"with __dbt__cte__paid as (select * from {R('stg_orders')} where status = 'paid'), "
               f"orders as (select * from __dbt__cte__paid) "
               f"select c.region, sum(o.amount) as revenue, count(*) as orders "
               f"from orders o join {R('stg_customers')} c using (customer_id) group by c.region")
        write(self.tmp / "dbt_project.yml", "name: shop\nprofile: shop\n")
        write(self.tmp / "seeds/raw_orders.csv", ORDERS)
        write(self.tmp / "seeds/raw_customers.csv", CUSTOMERS)
        for name, (a, b) in {"base": (stg, rev), "ok": (stg, rev.replace("count(*)", "count(1)")),
                             "bad": (stg.replace("status from", "lower(status) as status from"), rev)}.items():
            (self.tmp / f"{name}.json").write_text(json.dumps(manifest(a, b)))
        os.chdir(self.tmp)

    def test_change_in_staging_is_judged_on_the_mart(self):
        self._manifests()
        bad = self.check(manifest="bad.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertEqual(bad["inputs"]["dbt"]["changed_models"], ["stg_orders"])
        self.assertEqual(bad["inputs"]["dbt"]["compared"], ["revenue"])
        self.assertIn("case", {d["category"] for d in bad["differences"]})
        ok = self.check(manifest="ok.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        from fixwitness.report import write_outputs
        result = replay(json.loads(write_outputs(ok, self.tmp / "out").read_text()))
        self.assertTrue(result["reproduced"], result["problems"])

    def test_no_change_is_reported(self):
        self._manifests()
        with self.assertRaises(PlanError):
            self.check(manifest="base.json", base_manifest="base.json", engine="sqlite")

    def test_package_through_its_integration_tests(self):
        """A dbt package's sources read the integration tests' seeds; only what the outputs read runs."""
        from fixwitness.dbtmode import runnable_project, source_schema
        R = lambda n: f'"fixwitness"."pkg_tests"."{n}"'  # noqa: E731

        def manifest(stg):
            seed = lambda n: {"resource_type": "seed", "name": n, "package_name": "pkg_tests",  # noqa: E731
                              "original_file_path": f"seeds/{n}.csv", "relation_name": R(n), "schema": "pkg_tests"}
            model = lambda n, code, deps: {"resource_type": "model", "name": n, "package_name": "pkg",  # noqa: E731
                                           "language": "sql", "relation_name": R(n), "compiled_code": code,
                                           "config": {"materialized": "table"}, "depends_on": {"nodes": deps}}
            return {"metadata": {"adapter_type": "duckdb", "project_name": "pkg_tests"},
                    "sources": {"source.pkg.raw.orders": {"source_name": "raw", "name": "orders",
                                                          "identifier": "orders", "schema": "pkg_tests",
                                                          "relation_name": R("orders")}},
                    "nodes": {"seed.pkg_tests.orders": seed("orders"), "seed.pkg_tests.unused": seed("unused"),
                              "model.pkg.stg": model("stg", stg, ["source.pkg.raw.orders"]),
                              "model.pkg.rev": model("rev", f"select status, sum(amount) as total from {R('stg')} "
                                                            f"group by status", ["model.pkg.stg"]),
                              # Not read by the compared model: never built (it would fail if it were).
                              "model.pkg.broken": model("broken", "select * from no_such_table", [])}}

        write(self.tmp / "pkg/dbt_project.yml", "name: pkg\n")
        write(self.tmp / "pkg/models/stg.sql", "select 1\n")
        write(self.tmp / "pkg/integration_tests/dbt_project.yml", "name: pkg_tests\nprofile: x\n")
        write(self.tmp / "pkg/integration_tests/packages.yml", "packages:\n  - local: ../\n")
        write(self.tmp / "pkg/integration_tests/seeds/orders.csv", ORDERS)
        write(self.tmp / "pkg/integration_tests/seeds/unused.csv", "a,b\n1,2\n")
        tests = self.tmp / "pkg/integration_tests"
        self.assertEqual(runnable_project(self.tmp / "pkg"), tests)
        self.assertEqual(runnable_project(tests), tests)
        stg = f"select order_id, amount, status from {R('orders')}"
        for name, sql in {"base": stg, "ok": stg.replace("select order_id", "select  order_id "),
                          "bad": stg.replace("status from", "lower(status) as status from")}.items():
            (tests / f"{name}.json").write_text(json.dumps(manifest(sql)))
        self.assertEqual(source_schema(tests / "base.json"), "pkg_tests")
        os.chdir(tests)
        bad = self.check(manifest="bad.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertEqual(sorted(bad["inputs"]["tables"]), ["orders"])  # the unused seed is left out
        ok = self.check(manifest="ok.json", base_manifest="base.json", engine="sqlite")
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])


@unittest.skipUnless(os.environ.get("FIXWITNESS_DBT_PROJECT") and shutil.which("dbt"),
                     "needs dbt-core + dbt-duckdb and FIXWITNESS_DBT_PROJECT (a jaffle_shop checkout)")
class DbtProjectTests(TempDirTest):
    """dbt-labs' jaffle_shop, compiled by dbt itself: its orders model uses a Jinja loop."""

    def _project(self):
        src = Path(os.environ["FIXWITNESS_DBT_PROJECT"])
        repo = self.tmp / "repo"
        shutil.copytree(src, repo, ignore=shutil.ignore_patterns(".git", "target", "logs", "dbt_packages"))
        git(repo, "init", "-q")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "original")
        os.chdir(repo)
        return repo

    def test_wrong_and_correct_changes(self):
        repo = self._project()
        customers = repo / "models" / "customers.sql"
        original = customers.read_text()
        customers.write_text(original.replace("count(order_id)", "count(*)"))
        bad = self.check(path="models", max_cases=120)
        self.assertEqual(bad["verdict"], "FAIL", bad["reasons"])
        self.assertIn("customers", bad["inputs"]["dbt"]["changed_models"])
        customers.write_text(original.replace("final", "result"))
        ok = self.check(path="models", max_cases=120)
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])

    @unittest.skipUnless(os.environ.get("FIXWITNESS_TEST_POSTGRES") and importlib.util.find_spec("dbt.adapters.postgres"),
                         "needs a Postgres server and dbt-postgres (CI)")
    def test_compiled_and_run_in_postgres(self):
        """--warehouse: dbt compiles with the warehouse's own adapter, in a private schema that is
        dropped afterwards, and both versions run there."""
        import psycopg
        from fixwitness.warehouse import parse_url
        url = os.environ["FIXWITNESS_TEST_POSTGRES"]
        repo = self._project()
        customers = repo / "models" / "customers.sql"
        original = customers.read_text()
        customers.write_text(original.replace("count(order_id)", "count(*)"))
        bad = self.check(path="models", max_cases=40, warehouse=url)
        self.assertEqual(bad["verdict"], "FAIL", bad["reasons"])
        self.assertTrue(any("dbt-postgres adapter" in n for n in bad["notes"]), bad["notes"])
        self.assertEqual(bad["inputs"]["dbt"]["adapter"], "postgres")
        customers.write_text(original.replace("final", "result"))
        ok = self.check(path="models", max_cases=40, warehouse=url)
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        i = parse_url(url)
        with psycopg.connect(host=i["host"], port=i["port"], user=i["user"], dbname=i["path"]) as con:
            left = con.execute("select count(*) from information_schema.schemata where schema_name like 'fw_%'").fetchone()[0]
        self.assertEqual(left, 0)


@unittest.skipUnless(os.environ.get("FIXWITNESS_TEST_POSTGRES"),
                     "needs a Postgres server: FIXWITNESS_TEST_POSTGRES=postgres://USER@HOST:PORT/DB (CI)")
class WarehouseTests(TempDirTest):
    """Both versions run in a real Postgres server, each run in its own schema."""
    _sql_check = SqlModeTests._check

    def _check(self, after_sql, **extra):
        return self._sql_check(after_sql, warehouse=os.environ["FIXWITNESS_TEST_POSTGRES"], max_cases=40, **extra)

    def test_wrong_and_correct_changes_in_postgres(self):
        ok = self._check(REVENUE.replace("count(*) as orders", "count(1) as orders"))
        self.assertEqual(ok["verdict"], "PASS", ok["reasons"])
        self.assertEqual(ok["inputs"]["engine"], "warehouse")
        bad = self._check(REVENUE.replace("count(*)", "count(o.amount)"))
        self.assertEqual(bad["verdict"], "FAIL")
        self.assertIn("null-column", {d["category"] for d in bad["differences"]})

    def test_postgres_semantics(self):
        # DISTINCT ON exists in Postgres (not SQLite), and Postgres sorts NULLs first in DESC order:
        # the original picks an empty amount where max() skips it. Only the warehouse shows this.
        before = "select distinct on (customer_id) customer_id, amount from orders order by customer_id, amount desc"
        after = "select customer_id, max(amount) as amount from orders group by customer_id"
        proof = self._sql_check(after, before_sql=before, warehouse=os.environ["FIXWITNESS_TEST_POSTGRES"],
                                max_cases=40)
        self.assertEqual(proof["verdict"], "FAIL", proof["reasons"])

    def test_leftover_schemas_are_dropped(self):
        import psycopg
        from fixwitness.warehouse import parse_url
        self._check(REVENUE)
        i = parse_url(os.environ["FIXWITNESS_TEST_POSTGRES"])
        with psycopg.connect(host=i["host"], port=i["port"], user=i["user"], dbname=i["path"]) as con:
            left = con.execute("select count(*) from information_schema.schemata where schema_name like 'fw_%'").fetchone()[0]
        self.assertEqual(left, 0)



class WarehouseUnitTests(unittest.TestCase):
    def test_urls(self):
        from fixwitness.warehouse import ident, parse_url
        with self.assertRaises(ConfigError):
            load_config(None, {"warehouse": "postgres://u:secret@localhost/db"})  # recorded in the proof
        with self.assertRaises(ConfigError):
            load_config(None, {"warehouse": "mysql://u@localhost/db"})
        sf = parse_url("snowflake://me@xy12345/ANALYTICS?warehouse=WH&role=DEV")
        self.assertEqual((sf["host"], sf["path"], sf["query"]["warehouse"]), ("xy12345", "ANALYTICS", "WH"))
        self.assertEqual((ident("order_id", "snowflake"), ident("Order ID", "postgres")), ("order_id", '"Order ID"'))


class SetupTests(TempDirTest):
    def test_setup_merges_and_never_overwrites(self):
        from fixwitness.setup import setup
        root = self.tmp
        write(root / ".mcp.json", '{"mcpServers": {"other": {"command": "x"}}}')
        write(root / "etl" / "job.py", "import pandas as pd\n")
        out = setup("claude", root, instructions=True)
        data = json.loads((root / ".mcp.json").read_text())
        self.assertEqual(set(data["mcpServers"]), {"other", "fixwitness"})
        self.assertIn("prove_change", (root / "CLAUDE.md").read_text())
        self.assertIn("already has", setup("claude", root)[0])
        setup("vscode", root)
        self.assertEqual(json.loads((root / ".vscode" / "mcp.json").read_text())["servers"]["fixwitness"]["type"], "stdio")
        setup("github", root)
        wf = (root / ".github" / "workflows" / "fixwitness.yml").read_text()
        self.assertIn("install: duckdb,pandas", wf)
        self.assertIn("pull-requests: write", wf)
        write(root / ".pre-commit-config.yaml", "repos:\n  - repo: https://github.com/psf/black\n    rev: 24.1.0\n")
        setup("pre-commit", root)
        text = (root / ".pre-commit-config.yaml").read_text()
        self.assertIn("psf/black", text)
        self.assertIn("id: fixwitness", text)
        self.assertTrue(out)


class CliAndMcpTests(TempDirTest):
    def run_cli(self, *args, cwd=None, stdin=None):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        return subprocess.run([sys.executable, "-m", "fixwitness", *args], cwd=cwd or self.tmp, env=env,
                              input=stdin, capture_output=True, text=True, timeout=300)

    def test_init_then_check(self):
        repo = self.repo({"etl/clean.py": GitModeTests.BEFORE, "etl/sample.csv": SAMPLE})
        write(repo / "etl/clean.py", GitModeTests.SAFE)
        r = self.run_cli("init", "etl/clean.py", "--columns", "amount", cwd=repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('path = "etl/clean.py"', (repo / "fixwitness.toml").read_text())
        r = self.run_cli("check", cwd=repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)
        self.assertEqual(self.run_cli("check", "--dry-run", cwd=repo).returncode, 0)

    def test_command_line_paths_are_relative_to_current_folder(self):
        shutil.copytree(EXAMPLES, self.tmp / "examples")
        r = self.run_cli("check", "--config", "examples/pipeline_repair/fixwitness.toml",
                         "--after", "examples/pipeline_repair/load_payments_repair_naive.py")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("Incident resolved", r.stdout)

    def test_mcp_session(self):
        repo = self.repo({"etl/clean.py": GitModeTests.BEFORE, "etl/sample.csv": SAMPLE})
        write(repo / "etl/clean.py", GitModeTests.BEFORE.replace("eval(", "float("))
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "prove_fix", "arguments": {"path": "etl/clean.py", "columns": ["amount"]}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "prove_fix", "arguments": {"path": "etl/clean.py", "run_command": "curl {script} {input}"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
             "params": {"name": "prove_fix", "arguments": {"path": "etl/clean.py", "dry_run": True}}},
            {"jsonrpc": "2.0", "id": 6, "method": "no/such/method"},
        ]
        r = self.run_cli("mcp", cwd=repo, stdin="\n".join(json.dumps(m) for m in messages) + "\n")
        replies = [json.loads(line) for line in r.stdout.splitlines()]
        self.assertEqual([x["id"] for x in replies], [1, 2, 3, 4, 5, 6], r.stderr)
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual({t["name"] for t in replies[1]["result"]["tools"]}, {"prove_fix", "prove_change", "replay_proof"})
        call = replies[2]["result"]
        self.assertFalse(call["isError"], call)
        self.assertEqual(call["structuredContent"]["verdict"], "FAIL")
        self.assertTrue(call["structuredContent"]["differences"])
        self.assertTrue(Path(call["structuredContent"]["proof_path"]).is_file())
        self.assertTrue(replies[3]["result"]["isError"], "disallowed program must be refused")
        self.assertIn("mode", replies[4]["result"]["structuredContent"])
        self.assertEqual(replies[5]["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
