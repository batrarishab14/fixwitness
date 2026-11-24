# fixwitness

<!-- mcp-name: io.github.batrarishab14/fixwitness -->

**Evidence that an automated fix did what it claims, and nothing else.**

AI agents now patch vulnerabilities and repair broken pipelines on their own. Each of those changes needs a witness before it ships. fixwitness answers two questions about every fix:

1. **Did it fix the problem?**
   - For a security fix: does the exploit work on the original and fail on the fix?
   - For a self-healing repair: does the input that broke the job now go through?
2. **Did it change anything else?** fixwitness runs both versions on generated edge-case inputs and compares the output cell by cell.

You get a **verdict** (PASS / FAIL), a **confidence score** (0–100), a **proof record** anyone can replay, and a **runnable reproduction** of every difference. It needs no tests, only the sample data your repository already has. It runs from the command line, in CI (with a comment on the pull request), or **inside a coding agent over MCP**, so the agent checks its own change before it ships.

## One command for the whole change

```bash
fixwitness check          # in a git repo: every file you changed, against HEAD (or --base main)
```

Each changed file is checked the way that fits it. The sample data is found by name:

| Changed | Checked as |
|---|---|
| A file in a **dbt project** | The project compiled by dbt itself (with `dbt-duckdb`), so macros and packages work; seeds are the sample tables; the final models downstream of the change are compared |
| A **`.sql`** query | Its tables are the data files named after them (`orders.csv` for `orders`) |
| A **pandas, polars or PySpark** function that changed | Called with the data files named after its parameters; each side uses the library it imports |
| A **script** that reads CSV, JSON, JSON Lines or Parquet | Run on the sample next to it |
| Docs, data, config, tests | Listed as not checked, with the reason |

```
$ fixwitness check --no-attacks
## fixwitness: FAIL (3 checks)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `etl/revenue.py: revenue()` | dataframe | PASS 99/100 | - |
| `jobs/events.py` | script | **FAIL** | the fix changes output on 1 valid inputs |
| `models/revenue.sql` | sql | **FAIL** | the fix changes output on 2 valid inputs |

Not checked: `README.md` (not code)
```

Here `jobs/events.py` changed `e.get("status")` to `e["status"]`, which fails on an event without that key, and `models/revenue.sql` changed `count(*)` to `count(o.amount)`. Neither shows on today's data. For each difference, `.fixwitness/<check>/repro/<case>/` holds the input, both outputs and the commands to re-run each side, so you can confirm it yourself.

One file or a pair of files also works:

```bash
fixwitness check etl/clean_amounts.py            # one file: HEAD vs. your working copy
fixwitness check models/revenue.sql --table orders=seeds/orders.csv --table customers=seeds/customers.csv
fixwitness check --before old.py --after new.py --sample data/sample.csv
```

## SQL queries and dbt models

AI agents now repair data pipelines: Snowflake's agent goes from a failed pipeline to a pull request in about 16 minutes, and Databricks Genie ZeroOps tests its fixes on a copy of today's data before a person approves them. Neither describes checking the fix on data that isn't there yet ([research notes](docs/RESEARCH.md)).

fixwitness runs the original and the changed query on the same generated tables and compares the results. The tables are built from your sample tables, varied one at a time:
- an empty table;
- a NULL in each column, and a whole column of NULLs;
- a repeated row and a repeated key;
- values in another case or with padding;
- boundary and unusual numbers, dates and text;
- extra columns, including any that are new in the incident data.

```
$ fixwitness check models/revenue.sql --table orders=seeds/orders.csv --table customers=seeds/customers.csv
## fixwitness: FAIL
| Data unchanged | FAIL: 280 of 282 comparable valid inputs give the same output |
- `empty` input '' in `orders.amount`: changed
  - row 1, orders: '2' -> '1'
- `null-column` input '<all NULL>' in `orders.amount`: changed
  - row 1, orders: '2' -> '0'
```

That model's refactor swapped `count(*)` for `count(o.amount)`. On today's data the result is identical, so a data diff passes it. A single order with no amount shows the difference.

**On the SQL benchmark** ([`benchmark/sql/`](benchmark/sql/), 17 changes to 6 queries, each wrong change modelling a well-known SQL pitfall):

| Check | Wrong changes caught | Correct changes wrongly rejected |
|---|---|---|
| The query runs | 0/11 | 0/6 |
| Same result on the sample tables (a data diff on today's data) | 0/11 | 0/6 |
| **fixwitness** | **10/11** | **0/6** |
| **fixwitness + expected result for the incident** | **11/11** | **0/6** |

These are development results on SQLite: the SQL input classes were refined on this benchmark ([development log](study/DEVLOG_v0.6.md)). The held-out evaluation in [`study/PROTOCOL_v0.6.md`](study/PROTOCOL_v0.6.md) measures them on new tasks.

**How it runs SQL:**
- **Engine:** DuckDB when it is installed (`pip install duckdb`), otherwise SQLite from Python's standard library. Both versions always run on the same engine, which is recorded in the proof.
- **Types:** column types come from your sample tables. An empty cell is NULL. A value the column's type can't hold, such as `1,250` in a numeric column, is skipped, just as a warehouse would reject it.
- **Row order and numbers:** rows are compared as a set unless you pass `--sql-ordered`. Numbers are compared with a relative tolerance of 1e-9, because an equivalent query may add them up in a different order.
- **dbt models:** with `dbt-core` and `dbt-duckdb` installed, fixwitness runs `dbt seed` and `dbt compile` on both versions of the project in a private DuckDB file, so macros, packages, `var()` and `is_incremental()` are rendered by dbt. Or pass the `manifest.json` files your CI already has (`--manifest`, `--base-manifest`). Without dbt, `{{ ref('x') }}`, `{{ source('s', 'x') }}` and `{{ config(...) }}` are rendered by fixwitness, and other Jinja is refused with a message.
- **Incidents:** `--incident-table customers=customers_bad.csv` gives a table's contents when the original broke, and `--incident-expected` gives the correct result.

## Pipelines, warehouse SQL, DataFrames, JSON and Parquet

The same check works on the other places an agent changes data code:

| What changed | How fixwitness runs it | Example |
|---|---|---|
| **A dbt project or a folder of SQL models** | Every model, in dependency order (from `ref()` and the tables after `FROM`/`JOIN`). The final models, which no other model reads, are compared, so a change to a staging model is judged by what it does to the mart | `fixwitness check models/ --table orders=seeds/orders.csv` |
| **SQL written for a warehouse** | Translated with [sqlglot](https://github.com/tobymao/sqlglot) to DuckDB or SQLite; `analytics.raw.orders` becomes the loaded table `orders` | `--dialect snowflake` (or `bigquery`, `postgres`, `tsql`, ...) |
| **A pandas, polars or PySpark function** | Called with DataFrames built from your tables, with the sample's column types. Each side uses the library it imports, so a **pandas → polars migration** is checked too | `fixwitness check etl/revenue.py --function revenue --table orders=orders.csv` |
| **A script that reads JSON or JSON Lines** | Cases change one value at a path such as `user.country` or `items[].sku`: a missing key, `null`, a number written as a string, number spellings (`1e3`, `-0`, 30 digits), escapes, empty arrays and objects, an extra key, reversed key order | `--sample events.jsonl` |
| **A script that reads Parquet** | The typed-table cases, written back with the sample's Parquet schema. Parquet and JSON outputs are compared by value | `--sample orders.parquet` |

A polars rewrite of a pandas function, for example, can match it on today's data and still differ when a value is missing: pandas `size()` counts rows, but `pl.col("amount").count()` counts non-null values; and polars `group_by` keeps the group for a null key, which pandas `groupby` drops.

**On the benchmark for these kinds** ([`benchmark/complex/`](benchmark/complex/): a dbt project, a Snowflake query, a pandas function, a pandas → polars migration, a JSON Lines job and a Parquet job; 28 synthetic fixes, each modelling a known pitfall), run in CI on DuckDB with every library installed:

| Check | Wrong fixes caught | Correct fixes wrongly rejected |
|---|---|---|
| The job runs | 0/20 | 0/8 |
| Same output on the sample | 1/20 | 0/8 |
| **fixwitness** | **19/20** | **0/8** |

The miss is `round_each`: it rounds each amount before summing. That only shows when two records of the same country both have sub-cent amounts, and fixwitness changes one value at a time. The CI logs are on the [`ci-results`](../../tree/ci-results) branch. These are development results ([development log](study/DEVLOG_v0.6.md)).

## What it catches

A payments job started failing when the upstream system began sending amounts like `"1,250.00"`. A self-healing agent repaired it by stripping every character that isn't a digit or a dot. The job went green.

```
## fixwitness: FAIL
| Incident resolved | PASS: the original failed on `incident.csv` (ValueError: could not convert string to float: '1,250.00'); the fix processes it |
| Data unchanged    | FAIL: 29 of 35 comparable valid inputs give the same output |
- `numeric-format` input '-12.75' in `amount`: changed
  - row 2, amount_cents: '-1275' -> '1275'
```

The repair turned every refund into a charge. Its output on the sample file is identical, so a check against the sample alone, or a "did the job succeed?" check, passes it. The repair that only accepts thousands separators passes:

```
## fixwitness: PASS, confidence 91/100 (HIGH)
| Incident resolved | PASS: the original failed on `incident.csv` ...; the fix processes it |
| Data unchanged    | PASS: 35 of 35 comparable valid inputs give the same output |
```

The same thing happens with security fixes. Replacing `eval()` with `float()` closes a code-injection hole, but it also turns `1200` into `1200.0` everywhere downstream. fixwitness reports **FAIL** for it, and reports **PASS, 91/100** for the fix that preserves integers.

## Benchmark

There are 20 data jobs: 5 security fixes, 9 self-healing incident repairs and 6 refactors. Together they have 56 fixes: 21 correct and 35 wrong, with each wrong fix modelling a documented failure pattern. See [benchmark/](benchmark/README.md).

| Check | Wrong fixes caught | Correct fixes rejected |
|---|---|---|
| Job runs (what "pipeline is green" checks) | 3/35 (9%) | 0/21 |
| Regression test on the sample data | 6/35 (17%) | 0/21 |
| **fixwitness** | **29/35 (83%)** | **0/21** |
| **fixwitness + expected output for the incident** | **35/35 (100%)** | **0/21** |

The wrong fixes are synthetic, not agent output, and the benchmark was written by the tool's author. Read the [threats to validity](benchmark/README.md#threats-to-validity-read-before-citing) before citing these numbers. You can add real agent fixes and re-run it.

### Fixes written by AI assistants (20 November 2026)

The nine incident tasks were given to four chat assistants in one prompt each (`study/PROMPT_incidents.txt`), one run per assistant. Each fix was labelled by code review against the task's own rule: process the incident input correctly **without changing the output for any input the job already handled**. A "wrong" label cites a concrete input where the two programs differ.

| Assistant (model) | Fixes | Wrong by review (on a plausible input) | Rejected by: job runs | fixwitness 0.4.0 | fixwitness 0.5.0 |
|---|---|---|---|---|---|
| ChatGPT (free plan, default model) | 9 | 2 (2) | 0 | 0 | 2 |
| Claude (Haiku 5.5) | 9 | 2 (1) | 0 | 0 | 2 |
| Gemini (model selector: "Hydrogen") | 9 | 2 (1) | 0 | 0 | 2 |
| Microsoft Copilot (default model) | 9 | 1 (0) | 0 | 0 | 1 |
| **All** | **36** | **7 (4)** | **0** | **0** | **7** |

fixwitness 0.5.0 rejected none of the 29 correct fixes.

Every fix repaired the incident. Seven change the output on a file the job already handled:
- **I05, ChatGPT, Claude and Gemini:** these prefer `amount_usd` when a file has both `amount` and `amount_usd`.
- **I07, all four assistants:** each misreads some comma file.
  - ChatGPT's `csv.Sniffer` picks `;` when a text value mixes semicolons and quotes, as in `call back; "urgent"`.
  - The others decide from the first line, so they fail only on contrived headers.

**fixwitness 0.4.0 missed all seven.** Six need a different header, which 0.4.0 never varies. The seventh is triggered by a cell value that its catalogue lacked.

**fixwitness 0.5.0 catches all seven, but read this as development, not proof.** 0.5.0 was built after seeing these misses:
- it adds extra and reordered columns, odd header names, and values that mix delimiters with quotes;
- these are general input classes, written down in [a protocol](study/PROTOCOL_v0.5.md) before the code changed;
- every development run, including one that wrongly rejected two correct fixes, is in [the development log](study/DEVLOG_v0.5.md).

How well 0.5.0 does on fixes it has never seen will be measured on new tasks and fresh assistant runs, with the tool frozen first.

How the answers were captured, the labels and the evidence: [`study/`](study/README.md).

## Why this exists

- **Most AI patches aren't clean.** In 1Password's study of 6,080 AI-generated vulnerability patches (Aug 2026):
  - 53.9% left the vulnerability unresolved, introduced a new one, or both;
  - another 20.1% fixed it but changed unrelated behavior;
  - only 26% fully fixed it without changing behavior.
- **The big tools rely on your tests.**
  - Snyk's remediation agent verifies a fix by rescanning and running "the tests that exist in the application."
  - GitHub warns that Copilot Autofix "may suggest fixes that are syntactically valid but change the semantics of the program," and leans on your tests and CI to catch it.
  - Data scripts often have no tests.
- **Self-healing pipelines check for errors, not for changed numbers.** Typical self-healing dbt setups validate a repair with `dbt build` / `dbt test`. Nothing compares the output before and after the repair.
- **Fixing is now the bottleneck.** Anthropic's Project Glasswing update says progress is "limited by how quickly we can verify, disclose, and patch the large numbers of vulnerabilities found by AI."

## Who it's for

| You are | fixwitness lets you |
|---|---|
| Running self-healing agents on data pipelines | Auto-apply only the repairs that fix the incident without moving a single number |
| A reviewer with a queue of AI-generated fix PRs | Merge in seconds when a PR carries a PASS proof, and catch the ones that silently change data |
| Building a coding agent | Give it a tool to check its own work, and loop until it passes |
| Security, audit or GRC | Keep replayable evidence: which exact files, what was checked, what the result was |

More scenarios with ready-to-run commands are in [docs/USE_CASES.md](docs/USE_CASES.md): self-healing gates, autofix review, agent self-checks, refactors and rewrites, audit evidence, and measuring your own agents.

## Install

```bash
pip install "git+https://github.com/batrarishab14/fixwitness"
fixwitness demo
```

Python 3.11+, no dependencies. git is needed for the one-line mode. For SQL, DuckDB is used if installed (`pip install duckdb`), otherwise SQLite.

Optional, only for what you check: `dbt-core` and `dbt-duckdb` (dbt projects with macros), `sqlglot` (warehouse dialects), `pandas`, `polars` or `pyspark` (DataFrame functions), `pyarrow` (Parquet). `pip install "fixwitness[all] @ git+https://github.com/batrarishab14/fixwitness"` installs all but PySpark.

## Usage

| Situation | Command |
|---|---|
| You fixed one script (git) | `fixwitness check etl/clean.py` |
| A self-healing repair | `fixwitness check etl/load.py --incident failed_extract.csv --no-attacks` |
| Compare against a branch | `fixwitness check etl/clean.py --base main` |
| The fix is in an imported module or several files | `fixwitness check --command "python3 etl/run.py {input} {output}" --sample data/sample.csv` |
| No git: two files | `fixwitness check --before old.py --after new.py --sample sample.csv` |
| A rewrite in another language | `fixwitness check --before legacy.sh --after new.py --no-attacks` (each side's run command is detected) |
| A SQL query or dbt model (git) | `fixwitness check models/revenue.sql --table orders=seeds/orders.csv --table customers=seeds/customers.csv` |
| Two SQL files | `fixwitness check --before old.sql --after new.sql --table orders=orders.csv` |
| A dbt project (git) | `fixwitness check models/ --table orders=seeds/orders.csv --table customers=seeds/customers.csv` |
| Snowflake or BigQuery SQL | add `--dialect snowflake` (needs `pip install sqlglot`) |
| A pandas / polars / PySpark function | `fixwitness check etl/revenue.py --function revenue --table orders=data/orders.csv` |
| A job that reads JSON Lines or Parquet | `fixwitness check etl/events.py --sample data/events.jsonl --no-attacks` |
| See what would run | add `--dry-run` |
| Save the detected settings | `fixwitness init etl/clean.py`, then just `fixwitness check` |

**Detected for you:**
- **Interpreter:** taken from the file extension or the shebang line.
- **Calling convention:** fixwitness tries `script input output`, then `script input` with output on stdout, then `script < input`. It keeps the first one that works on the original.
- **Sample file:** found automatically when there is exactly one CSV next to the script, or in a `data/`, `fixtures/` or similar folder.

**In git mode:**
- Both versions run from full snapshots of the repository: the original from the base commit, the fix from your working tree.
- Changes to imported modules and config files are therefore compared correctly.
- Your files are never modified. fixwitness only writes to `.fixwitness/`, which it tells git to ignore.

**Options:**

| Option | What it does |
|---|---|
| `--incident file.csv` | The input that broke the job. PASS requires the fix to process it with the same output columns, and one row per input row when the original always writes one |
| `--incident-expected out.csv` | The correct output for the incident input, when you know it |
| `--no-attacks` | Skip attack payloads (repairs and refactors) |
| `--columns amount` | Probe only the columns the problem is about |
| `--review shell-metachar,quotes` | Report differences in these categories without failing |
| `--ignore-columns run_id` | Leave these output columns out of the comparison |
| `--ignore-pattern '\d{4}-\d\d-\d\d'` | Mask volatile text such as timestamps |
| `--tolerance 1e-9` | Allow tiny floating-point differences |
| `--unordered` | Ignore row order |
| `--no-network` | Run without network access (Linux user namespaces) |
| `--min-confidence 90` | Fail below this score |
| `--table NAME=FILE.csv` | SQL/dbt: a table the query reads and its sample data (repeat for each table) |
| `--incident-table NAME=FILE.csv` | SQL/dbt: a table's contents when the original broke |
| `--engine duckdb` | SQL/dbt: the engine (default: DuckDB if installed, else SQLite) |
| `--sql-ordered` | SQL/dbt and DataFrames: compare result rows in order |
| `--sql-outputs revenue,churn` | A folder of models: the models to compare (default: the final ones; `all` for every model) |
| `--dialect snowflake` | SQL/dbt: the warehouse the SQL is written for; translated with sqlglot |
| `--function NAME` | Python: the DataFrame function to call; name the tables after its parameters |
| `--library polars` | Python: the DataFrame library (default: from the script's imports) |
| `--output json` | Compare outputs as JSON (the default when the input is JSON) |

Columns that change between two runs of the original on the same input, such as IDs or timestamps, are detected and ignored automatically, and listed in the report.

Exit codes: `0` PASS, `1` FAIL / INCONCLUSIVE / below `--min-confidence`, `2` usage error.

## Inside a coding agent (MCP)

```bash
claude mcp add fixwitness -- fixwitness mcp      # Claude Code
```

```json
{ "mcpServers": { "fixwitness": { "command": "fixwitness", "args": ["mcp"] } } }
```

**Tools:**
- `prove_fix`. Simplest calls:
  - `{"path": "etl/clean.py"}` for a security fix;
  - `{"path": "etl/load.py", "incident_path": "failed.csv", "attacks": false}` for a repair.
- `replay_proof`.

**What the server tells the agent:**
- run `prove_fix` before proposing, committing or deploying a change;
- on FAIL, read the listed differences, adjust and retry;
- ship only on PASS, with the proof ID in the PR.

**Safety:** the MCP server always enforces the program allow-list.

## In CI (GitHub Action)

```yaml
on: pull_request
jobs:
  fixwitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0              # the base commit must be available
      - uses: batrarishab14/fixwitness@v0.6.0
        with:
          install: duckdb,dbt,pandas    # only what your code needs
          args: --no-attacks            # data changes, not security fixes
```

With no `path`, the Action checks every file the pull request changed, against its base commit. The report is posted as one comment on the pull request and updated on every push; add `permissions: {contents: read, pull-requests: write}` to the job. It also appears in the job summary, and the proofs and reproductions are uploaded as an artifact. To make proofs tamper-evident, add GitHub artifact attestations (`actions/attest-build-provenance`, `subject-path: fixwitness-report/proof.json`).

## How it works

```
sample.csv ─► cases: edge-case values + attack payloads ─► run ORIGINAL ─┐
incident.csv ─► incident check ──────────────────────────► run FIX ──────┴─► compare ─► verdict, score, proof.json
```

1. **Cases.** For each probed column, fixwitness swaps values from a catalogue into the first rows of your sample:
   - number formats (`1200`, `-12.75`, `1e3`, `1_000`, `-0.0`);
   - whitespace, empty cells, Unicode, case and punctuation;
   - quotes, CSV quoting and very long values;
   - shell metacharacters;
   - values that mix another delimiter (`;`, tab, `|`) with quotes;
   - plus a header-only file and CRLF line endings.

   It also changes the file's structure, keeping the data:
   - **schema:** an extra column, including each column that is new in the incident file, and the columns in another order;
   - **header names:** an added column whose name holds `;`, tab, `|`, quotes, a comma, a line break, spaces, Unicode, or nothing, placed first and last.

   A program that reads columns by name gives the same output on all of these, so a fix that doesn't is flagged.
2. **Incident (repairs).** The original must fail on the incident input, and the fix must process it.
3. **Attacks (security fixes).**

   | Family | Payloads | Oracle |
   |---|---|---|
   | command injection | `$(...)`, backticks, `;`, `&&`, `\|` | must create a marker file in a private directory |
   | code injection | Python `__import__` | must create a marker file in a private directory |
   | path traversal | `../../..` and absolute paths | must land a file in that private directory |
   | template injection | `{{7*7919}}` and similar | detected when `55433` appears in the output |
4. **Runs.**
   - The original and the fix run in the same fresh directory, one after the other, so paths can't cause false differences.
   - The environment is minimal (fixed `TZ`, locale and hash seed) and each run has a timeout. On timeout the whole process group is killed.
   - No shell builds the command line.
5. **Compare.** CSV is compared cell by cell. Quoting or line-ending differences count as the same data.
6. **Verdict.**
   - **PASS:** the problem is fixed, no attack works on the fix, and every comparable valid input gives the same output.
   - Inputs the original itself fails on are reported as *not comparable*.

## The confidence score

The score is a transparent heuristic, not the probability that the fix is correct.

```
score = 100 × (1 − 3/n) × r
```

- **n** is the number of valid inputs that gave the same output. With zero differences in *n* inputs, the "rule of three" puts the 95% upper bound on the share of such inputs the fix would change at about 3/*n*.
- **r** is 1.0 when every claim was demonstrated on the original (the exploit worked on it, the incident input broke it). Otherwise it is 0.7.
- The score is **0** unless the verdict is PASS.

Bands: **HIGH** ≥ 90, **MEDIUM** ≥ 75, **LOW** below that.

## The proof record

`.fixwitness/proof.json` holds:
- the SHA-256 of every input (files, or the base commit plus every changed file, the sample and the incident);
- the resolved command, settings and seed;
- every case and its result;
- the verdict, the score, the differences and the limitations.

```bash
fixwitness replay .fixwitness/proof.json
# REPRODUCED: proof 26e3dc609eebf564 gives the same evidence (verdict PASS).
```

Replay refuses to run if any input changed. Otherwise it re-runs everything and compares the evidence hash.

## Examples

`src/fixwitness/examples/` has three cases. Each includes the original, the obvious fix and a correct fix:

| Example | Problem | Obvious fix | What it breaks |
|---|---|---|---|
| `pipeline_repair` | Job crashes on `"1,250.00"` | Keep only digits and dots | Refunds become charges; `1e3` becomes 13 |
| `python_eval` | `eval()` on a CSV amount (CWE-95) | `float()` | Whole numbers become `1200.0` |
| `shell_eval` | `eval echo $region` (CWE-78) | Remove `eval` | Spaces are no longer trimmed |

## Limits

- **Not a formal proof.** It is differential testing: evidence on the input categories it generates.
- **Not a scanner and not an agent.** It checks fixes made by Claude Code, Copilot, Snyk, a self-healing system or a person.
- **Not a sandbox.** Scripts run as your user. Use `--no-network`, a container or CI for untrusted code.
- **Inputs are CSV, JSON, JSON Lines or Parquet** for scripts. Any program in any language works, as long as it reads a file or stdin.
- **One value changes at a time.** A difference that needs two unusual values together (two records of the same key, each with a sub-cent amount) can be missed.
- **SQL runs on DuckDB or SQLite,** not on your warehouse. Warehouse SQL is translated with sqlglot; a function it can't translate fails to run. Results are evidence for the logic, not for warehouse-specific behaviour.
- **dbt support covers models** with `ref()`, `source()` and `config()`, one at a time or as a folder. For macros and other Jinja, check the compiled SQL. Incremental models are run as full builds.
- **DataFrame functions take about half a second per run** (the library is imported each time, so every run is isolated). Keep `--max-cases` modest for PySpark, which starts a local session per run.
- **Four attack families** only. SQL injection, deserialization and SSRF are not tested yet.

## Roadmap

- dbt projects through dbt itself (macros, seeds, incremental models).
- Faster DataFrame runs (one import, a forked process per run).
- SQL-injection payloads.
- Reading the finding from SARIF.
- A container runner.
- Signed proofs.

## Sources

- [1Password: Why AI-generated patches still require human review (Aug 2026)](https://1password.com/blog/why-ai-generated-patches-still-require-human-review)
- [Snyk remediation agent docs](https://docs.snyk.io/scan-fix-and-prevent/fix/remediation-agent)
- [GitHub: Responsible use of Copilot Autofix](https://docs.github.com/en/enterprise-cloud@latest/code-security/responsible-use/responsible-use-autofix-code-scanning)
- [Paradime: Building self-healing pipelines for dbt projects](https://www.paradime.io/guides/dbt-self-healing-pipelines)
- [Anthropic: Project Glasswing initial update (May 2026)](https://www.anthropic.com/research/glasswing-initial-update)

## License

MIT © 2026 Rishab Batra
