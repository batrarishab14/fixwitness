# Real-repository study: protocol

Written and committed before fixwitness was run on any of these commits. The candidate list and
its labels (`candidates.csv`) are frozen in the same commit.

## Questions

1. **Real bugs.** Would fixwitness have caught each real bug that maintainers of widely used dbt
   packages later fixed?
2. **Real refactors.** On real changes that their authors described as having no effect on the
   data, how often does fixwitness say the outputs differ, and how many of those differences are
   false alarms?

## Corpus

Fivetran's public dbt packages (github.com/fivetran/dbt_*): 36 transformation packages and 30
source packages, cloned with full history. They were chosen because:

- they are widely used, and maintained by a company rather than by us;
- every release is described in `CHANGELOG.md` under fixed headings ("Bug Fixes", "Under the
  Hood", "Feature Updates", "Schema/Data Change", ...), which gives a label that we did not write;
- each package has an integration-test project (`integration_tests/`) with seed data, which
  fixwitness uses as its sample. We do not write or change any data.

## Selecting commits (`mine.py`)

A release is a candidate when its CHANGELOG entry names exactly one pull request, that pull
request is one commit on the main line (squash-merged "... (#N)" or a merge commit "Merge pull
request #N"), and the commit changes at least one `.sql` file in `models/` or `macros/`.
The original is the commit's first parent; the change is the commit.

From the CHANGELOG headings (`mine.py`, function `kind`):

- **bug** set: every heading is a bug-fix heading ("Bug Fix", "Bug Fixes", "Fixes", ...), apart
  from Documentation, Under the Hood, Contributors, Dependencies, Tests and Quickstart headings.
  Releases that also add features or change schemas are left out, so that any difference found
  comes from the fix.
- **refactor** set: every heading is Under the Hood, Documentation, Contributors, Dependencies,
  Tests or Quickstart.

## Labels (`candidates.csv`, columns `label` and `why`)

Each bug-fix release was read and labelled once, from its CHANGELOG text only:

- `wrong-data`: the text describes wrong output (values, rows, duplicates, nulls, types) in the
  package's default configuration, on any warehouse.
- `crash-on-data`: the model fails on some data (divide by zero, a failed cast, an empty table) in
  the default configuration, on any warehouse.
- `out:<why>`: outside the question, not run in the headline numbers: `warehouse` (one warehouse
  only: BigQuery, Snowflake, Databricks, Redshift or Postgres types), `compile` (a compile or parse
  error, not data), `config` (only with a non-default variable, several unioned connections,
  History Mode or Quickstart), `incremental` (incremental runs only), `source-type` (depends on
  the connector's column names or types), `feature` (adds a field or model).
- `duplicate`: the same commit as another release (a pre-release and its general release).
- Two bug-fix releases whose text describes only a refactor (CTE renames; a performance rewrite)
  are moved to the refactor set.

Each refactor release was labelled `refactor`, or `out:announced` when its text announces a change
to output values, types or column order despite the heading (for example "casts ids to string").

Counts at freezing: bug set 60 `wrong-data` + 13 `crash-on-data` = 73 in scope (82 out of scope,
6 duplicates); refactor set 43 `refactor` (10 `out:announced`, 2 duplicates).

## Running (`run_study.py`, workflow `study.yml`)

For each candidate: check out the commit, then run the command a user would run, with defaults:

    fixwitness check --base <parent> --no-attacks

(whole-change mode: no file named, no sample given, no configuration). fixwitness finds the
package's integration-test project, builds both versions on the seeds with dbt-core and
dbt-duckdb, and compares the final models downstream of the change on generated inputs. One run
per candidate, seed 0, at most 25 minutes. dbt-core and dbt-duckdb are the latest releases at run
time; their versions are recorded.

## Measures

- **Bug set.** Caught: the verdict is FAIL (some valid input gives a different output). Also
  reported: a difference only on inputs held for review; PASS (missed); not checked (with the
  reason: the project did not compile, no SQL changed after compiling, a timeout).
  Catch rate = caught / checked, with the not-checked count shown beside it.
- **Refactor set.** Each FAIL is inspected from its reproduction and labelled **real** (the outputs
  really differ, with the input and the two outputs) or **false alarm** (they do not, or the
  difference comes from fixwitness itself, with the cause). False-alarm rate = false alarms /
  checked. A real difference in a release described as having no effect is reported as found.
- Every result row links to its proof (`summary.json`, `report.md`).

## What this does not show

- Whether the difference fixwitness finds for a bug is the one described: any difference counts
  as caught, because the change contains only the fix. A sample of findings is read and compared
  with the CHANGELOG text, and reported as such.
- Results on warehouses other than DuckDB, on projects without seed data, or on code other than
  Fivetran's.
- fixwitness was not tuned on these commits. Changes made only so that it can run on them (finding
  the integration-test project, sources that read seeds) were made before the first run and are
  listed in RESULTS.md. If anything that changes a verdict is changed after a run, the numbers
  before and after are both reported.

## Amendments (all made before the first counted run)

**2026-11-24, warehouse.** The candidates are compiled and run on **Postgres 16 with dbt-postgres**
(`fixwitness check --base <parent> --no-attacks --warehouse postgres://...`), not on DuckDB.
Reason: Fivetran added DuckDB to these packages' integration tests only recently, and in the
pilots older commits failed to load their seeds on DuckDB (`dbt seed` errors), while Postgres has
been a supported warehouse of every package throughout. Each shard has its own Postgres server;
each compile uses a private schema that is dropped afterwards. What the protocol measures is
unchanged.

**2026-11-24, correction.** An earlier version of this section, and the after_freeze.csv list,
called commit 3f3c4a0 "Fivetran's fix of dbt_lever#43". It is not: it is our own fix, applied to a
local clone. dbt_lever#43 is still open; it is handled as an open bug report (open_issues/lever-43).

**2026-11-24, changes to fixwitness made from the pilots.** Pilot runs, on 8 of the
candidates and on two open bug reports (dbt_lever#43, dbt_zendesk#284), were used only to make the study run;
their verdicts are not counted and were not used to tune case generation. Changes since the list
was frozen (commit 0c44e21): seeds are loaded with the column types dbt gave them (booleans and
timestamps were text, so models using them failed on every input); keys are linked across tables
when the sample's tables share no key values; true/false and time-boundary cases for typed
columns; dbt errors are reported with dbt's own explanation; dbt compiles with the warehouse's
own adapter when a warehouse is given. fixwitness's verdict rules are unchanged.

**2026-11-24, seeds.** Many bug-fix commits also add seed rows that show the bug (for example
"adjusted the invoice_line_item seed data to include quantity = 0"). The sample fixwitness uses
must be the data available before anyone knew of the bug, so before each run the commit's
changes to `.csv` files are undone in the working tree (changed files put back as in the parent,
added files removed); only code changes are compared. The number of files put back is recorded
per candidate (`seeds_restored`). A candidate that cannot be built without its new seed files is
reported as not checked.

**2026-11-24, direction for bug fixes.** A bug fix is run in the direction the bug arrived: the
fixed commit is the original (`--base <commit>`) and the parent, which has the bug, is the change
(checked out as the working tree, with its own seed data). The question becomes the one a team
asks before merging: would fixwitness flag the change that introduces this bug? This also makes
crash-on-data bugs count: the bug-introducing change fails on inputs the fixed version handles,
which is a finding ("the fix fails where the original worked"), whereas run the other way an
input on which only the original fails cannot be compared. Refactors keep the commit's direction
(parent, then commit), with the parent's seed data. Caught is still: verdict FAIL.

**2026-11-24, incremental models.** Since the project is built before it is compiled, `dbt compile`
runs with `--full-refresh`, so incremental models compile as full builds rather than as updates of
themselves.

**2026-11-24, which models are compared.** fixwitness compared only the final models downstream of
a change (models no other model reads). A pilot on the open report dbt_lever#43 showed why that is
wrong for packages: the bug is in `lever__interview_enhanced`, a published mart, but another mart
reads it, so only that other mart was compared and the duplicated rows did not show. fixwitness now
compares every published model downstream of the change (dbt's structure: not staging or
intermediate models), plus the final ones. The pilot was on an open report, not on a candidate.
