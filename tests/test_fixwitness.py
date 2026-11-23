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
        with self.assertRaises(ConfigError):
            load_config(None, {})
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
        self.assertIn("several CSV files", str(ctx.exception))


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
        self.assertEqual({t["name"] for t in replies[1]["result"]["tools"]}, {"prove_fix", "replay_proof"})
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
