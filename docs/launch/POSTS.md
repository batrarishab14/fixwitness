# Launch posts (drafts, not posted)

Numbers in {braces} are filled in from `benchmark/realrepo/RESULTS.md` once the study run is final.
Post only after `pip install fixwitness` works (PyPI) and the v0.6.0 release exists.

---

## Show HN

**Title:** Show HN: fixwitness – check that a data-code change only changes what it should

AI agents and people both change dbt models, SQL and pandas code every day. Code review reads the
diff; tests check the cases someone thought of. Neither tells you what the change does to the
data you haven't seen yet.

fixwitness runs the original and the changed version on generated edge cases built from the sample
data your repository already has (NULLs, repeated keys, case and whitespace variants, boundary
numbers and times, rows linked across tables), compares the outputs cell by cell, and gives a
verdict, a plain-English finding, the smallest input that shows it, and a proof anyone can replay.
No production data, no tests to write. For a bug fix, `--expect-change revenue.total` passes only
if nothing but that column changes.

On real code: we froze a list of {N} real bug fixes and {M} refactors from Fivetran's public dbt
packages (from their changelogs) before running anything, and ran fixwitness with defaults on
Postgres. It caught {X} of {Y} checkable bugs, with {Z} false alarms on {W} refactors. Two open bug
reports in those packages are fixed with a fixwitness proof attached. Method, results and every
proof: {link to RESULTS.md}.

`pip install fixwitness`, then `fixwitness check` in a git repo. It also runs as an MCP server, so
a coding agent can check its own change before it opens a pull request.

What it is not: a formal proof (it's differential testing), or a replacement for dbt tests (it
uses them: inputs that break your unique / not_null / accepted_values tests are reviewed, not
failed).

---

## r/dataengineering

**Title:** I built an open-source tool that tells you what your dbt/SQL change does to data you haven't seen yet (tested on {N}+{M} real Fivetran package commits)

{same body, shorter; lead with the dbt example and the study table}

---

## dbt Community Slack (#tools-and-integrations)

fixwitness checks a dbt change before you merge it: it builds both versions with dbt itself (DuckDB,
or your warehouse's adapter), generates edge-case inputs from your seeds, and compares the final
models downstream of the change. Your own dbt tests are used as data rules, so it doesn't flag
inputs your project says can't happen. For a bug fix, `--expect-change model.column` proves that
only that column changes. Tested on {N}+{M} real commits from Fivetran's packages: {results}.
{link}

---

## LinkedIn

Data teams now let AI agents edit dbt models and SQL. The question that matters before merge is
not "does it compile" but "what does this change do to the numbers?"

I've been building fixwitness, an open-source tool that answers that with evidence: it runs the old
and new code on generated edge cases from the sample data a repo already has, and shows exactly
what changes, on which inputs, in plain English, with a proof anyone can re-run.

To test it honestly, I froze a list of {N} real bug fixes and {M} refactors from Fivetran's public
dbt packages before running anything. Results: {X}/{Y} bugs caught, {Z} false alarms on {W}
refactors. {link}
