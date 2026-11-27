---
name: fixwitness-check
description: Use before finalizing, committing, or proposing a change to a SQL query, a dbt model, or a data pipeline file (Python/pandas/polars/PySpark/Parquet/JSON) in this project -- whenever a "fix", "bug fix", "repair", or small edit to existing data-transformation logic is about to be shipped. Runs fixwitness, which compares the original and changed code on realistic varied inputs and fails if the fix changes output it shouldn't, or silently doesn't fix what it claims to. Do not use for brand-new models/pipelines with no prior version, or for changes with no data-shape impact (formatting, comments, docs).
---

# fixwitness: verify a data-pipeline fix before shipping it

fixwitness is an oracle-free differential tester for SQL, dbt and data-pipeline code. It builds the
original and the changed version of the file, generates realistic varied inputs (edge cases, nulls,
duplicates, boundary values -- not random fuzzing), runs both versions, and reports where their outputs
differ. It does not need a human-written "expected output" to compare against.

Use this skill reflexively, the way you'd run existing tests, whenever you are about to finalize a change
to:
- a `.sql` file or dbt model,
- a Python/pandas/polars/PySpark pipeline step,
- any file whose job is to transform or aggregate data and that already has a prior (committed) version.

Do NOT use it for: a brand-new model/pipeline being written for the first time (there's no "original" to
diff against), a change with no data-shape impact (renaming a variable, fixing a comment, reformatting), or
a change you have not yet finished writing.

## Steps

1. **Check fixwitness is available.** Run `fixwitness --version`. If that fails:
   - If network/package installs are allowed in this environment: `pip install fixwitness` (or
     `pip install --break-system-packages fixwitness` if needed), then retry.
   - If installs are not allowed here, say so plainly in one line and skip the rest of this skill rather
     than blocking the task -- do not fail the user's request over a missing optional check.

2. **Run the check**, from the repository root, against the change you just made:
   - A single file: `fixwitness check <path/to/file> --no-attacks` (drop `--no-attacks` for a security fix,
     where attack payloads are relevant).
   - A whole dbt project: `fixwitness check --no-attacks` (compiles both versions with dbt and compares the
     published models).
   - If the fix is supposed to change specific, known columns only (you know this from the bug description),
     add `--expect-change <table>.<column>[,<table>.<column>...]` -- this tells fixwitness to fail if
     anything else changes too, which is a stronger, more useful check than a bare diff.

3. **Read the verdict, don't just glance at pass/fail:**
   - `PASS`: no difference found across every generated input. For a claimed bug fix, this is suspicious, not
     reassuring -- it usually means the fix doesn't do anything observable on the available test data,
     not that it's correct. Say so plainly rather than treating PASS as "safe to ship."
   - `FAIL`: a real difference was found. Read the listed differences in the report (`fixwitness-report/`)
     before deciding whether the fix is wrong or the check's expectation (`--expect-change`) was too narrow.
   - `not-comparable` / inconclusive: the original or changed version itself failed to run (a compile error,
     an unrelated crash). This is not a verdict on the fix -- investigate and report the real error rather
     than treating it as a pass.

4. **Report the verdict and the proof path to the user before they commit or open a PR.** Include the proof
   ID if one was produced, so it can be cited in the commit message or PR description. Never silently
   proceed past a FAIL or an inconclusive result without telling the user.

## What this does and doesn't catch

fixwitness is strongest at: a fix that changes more rows/columns than intended, a fix that only works on the
specific example in the bug report and not nearby cases, and a repair whose claimed effect doesn't actually
show up anywhere. It is weakest when the project's own test/seed data doesn't contain the row combination
the bug's precondition needs -- in that case it will report PASS even on a genuinely unfixed bug. A PASS is
evidence of "no observed regression," not proof of correctness.
