# Use cases

Each use case below says who it's for, what goes wrong today, and the exact command. The "today" problems are backed by the sources in the main README and the benchmark.

---

## 0. Review an agent's pull request in one step

**Who:** anyone whose AI agent opens pull requests against data code.

**What goes wrong today:** the PR touches a dbt model, a pandas function and a job script; CI runs the existing tests, which don't cover what changed, and the reviewer reads the diff.

**With fixwitness:** one check covers every changed file, each the way that fits it, and comments on the pull request with a row per file.

```bash
fixwitness check --base main --no-attacks
```

```yaml
# .github/workflows/fixwitness.yml
on: pull_request
permissions: {contents: read, pull-requests: write}
jobs:
  fixwitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: batrarishab14/fixwitness@v0.6.0
        with: {install: "duckdb,dbt,pandas", args: "--no-attacks"}
```

---

## 1. Gate the repairs of a self-healing pipeline

**Who:** data platform teams running agents that fix failed jobs automatically.

**What goes wrong today:** the agent's repair is accepted when the job runs again without errors. In the benchmark, that check caught **3 of 20** wrong incident repairs. Repairs that turned refunds into charges, dropped rows or filled in zeros all passed.

**With fixwitness:** the repair is applied automatically only if fixwitness passes. Otherwise it goes to a person, with the differences listed.

```bash
fixwitness check etl/load_payments.py \
  --incident failed/extract_2026-11-12.csv \
  --no-attacks --min-confidence 90
# exit 0 -> auto-apply; exit 1 -> open a ticket with .fixwitness/report.md
```

**What fixwitness checks:**
- the incident input now goes through;
- the output columns are the same as before;
- there is one output row per input row, when the original always writes one;
- every edge-case input gives the same output as before.

If you know the right answer for the incident rows, add `--incident-expected expected.csv`. That closes the last gap the benchmark found: repairs that fill in a plausible but wrong value.

---

## 2. Review AI-generated security fixes faster

**Who:** reviewers facing a queue of fixes from Copilot Autofix, Snyk Agent Fix, Claude Code or similar tools.

**What goes wrong today:** the fix is "verified" by a rescan plus whatever tests exist. In 1Password's study of 6,080 AI-generated patches, only 26% fixed the vulnerability without changing behavior.

**With fixwitness:** the attack payloads are run against both versions, so the hole is shown open on the original and closed on the fix. Then every edge-case input is compared. A pull request that carries a PASS proof needs a short review; a FAIL lists exactly what changed.

```yaml
# .github/workflows/fixwitness.yml
on: pull_request
jobs:
  fixwitness:
    if: contains(github.event.pull_request.labels.*.name, 'autofix')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: batrarishab14/fixwitness@v0.4.0
        with: { path: etl/clean.py, min-confidence: 90 }
```

---

## 3. Let a coding agent check its own work

**Who:** anyone using Claude Code, Cursor or another MCP-capable agent on data code.

**What goes wrong today:** the agent says "done" when the code runs.

**With fixwitness:** the agent calls `prove_fix` and keeps iterating until the verdict is PASS. The server's instructions tell it to do this before proposing a change.

```bash
claude mcp add fixwitness -- fixwitness mcp
```

Then ask, for example: *"Fix the eval() finding in etl/clean.py. Use fixwitness to prove the fix before you finish."*

---

## 4. Verify refactors, upgrades and rewrites

**Who:** teams modernising legacy scripts: shell to Python, a Python version upgrade, a library swap, "clean up this code."

**What goes wrong today:** the code looks equivalent but isn't. Typical changes: `round()` instead of half-up rounding, `casefold()` instead of `lower()`, `//` instead of truncation, keeping the last duplicate instead of the first. In the benchmark, a regression test on the sample data caught **2 of 6** of these. fixwitness caught all 6.

```bash
fixwitness check --before legacy/normalize.sh --after new/normalize.py --sample data/sample.csv --no-attacks
# run commands are detected per file: bash for the original, python3 for the rewrite
```

---

## 5. Evidence for change management and audit

**Who:** security, risk, GRC and audit teams that must show how a change to a report-producing job was verified.

**What goes wrong today:** the evidence is a ticket comment saying "tested."

**With fixwitness:** every check writes `.fixwitness/proof.json`. It contains the SHA-256 of the exact files, the settings and seed, every input category tried, the result per input, and the verdict. Anyone can re-run it later; replay refuses if any file has changed.

```bash
fixwitness replay .fixwitness/proof.json
# REPRODUCED: proof 26e3dc609eebf564 gives the same evidence (verdict PASS).
```

Whether this satisfies a specific control or regulation is for your auditors to decide. fixwitness provides the evidence, not the compliance determination.

---

## 6. Measure your own agents

**Who:** teams deciding whether to trust an agent with fixes at all.

**What goes wrong today:** there's no data on how often the agent's "fixed" is actually right on your kind of code.

**With fixwitness:** run the benchmark prompts through your agent, drop its answers into `benchmark/agents/<agent>/`, and get a table of which fixes pass and why. See [benchmark/README.md](../benchmark/README.md).

---

## 7. Migrate pandas to polars or PySpark, or a warehouse to another

**Who:** teams moving DataFrame code to a faster library, or SQL from one warehouse to another.

**What goes wrong today:** the rewrite is checked on today's data, where it matches. The usual slips are about missing values: pandas `size()` (rows) translated to polars `count()` (non-null values), or a polars `group_by` that keeps the null group pandas `groupby` drops.

**With fixwitness:** each side runs with the library or dialect it is written in, on the same generated tables.

```bash
# the original imports pandas, the rewrite imports polars: each is called with its own DataFrames
fixwitness check --before etl/revenue_pandas.py --after etl/revenue_polars.py --function revenue \
  --table orders=data/orders.csv --table customers=data/customers.csv

# a Snowflake model refactored: translated with sqlglot, run on DuckDB
fixwitness check models/revenue.sql --dialect snowflake --table orders=seeds/orders.csv
```

---

## 8. A change anywhere in a dbt project

**Who:** analytics engineers whose agent edits a staging model.

**What goes wrong today:** the staging model's own test passes; nobody compares the marts built on it.

**With fixwitness:** point it at the models folder. Every model runs in dependency order, and the final models (those no other model reads) are compared.

```bash
fixwitness check models/ --table orders=seeds/orders.csv --table customers=seeds/customers.csv
fixwitness check models/ --sql-outputs revenue,churn ...   # or name the models to compare
```

---

## 9. Jobs that read JSON or Parquet

**Who:** teams whose jobs read event streams (JSON Lines), API responses (JSON) or lake files (Parquet).

**What goes wrong today:** a refactor reads `e["status"]` where the original read `e.get("status")`, or wraps a value in `float()`. Today's events all have the key and small numbers, so nothing shows.

**With fixwitness:** cases leave a key out, set it to `null`, write a number as a string or with 30 digits, add keys and reverse key order. JSON and Parquet outputs are compared by value.

```bash
fixwitness check etl/events.py --sample data/events.jsonl --no-attacks
fixwitness check etl/orders.py --sample data/orders.parquet --no-attacks   # needs pyarrow
```
