# The problem fixwitness addresses: checking an AI agent's change to a data transformation

Research notes, 23 November 2026. Every claim is cited. Lines marked *(inference)* are the author's reading of the sources.

## 1. AI agents now change production data pipelines

- **Snowflake** runs an agent that investigates every monitored pipeline failure. It goes "from incident detection to a ready-to-review PR in under 16 minutes on average", and "a person still decides what ships" [1].
- **Databricks Genie ZeroOps** (16 June 2026) detects failures, traces their cause through lineage and generates a fix. The fix is tested in a sandbox: "the proposed fix runs against real data there, never against production, and nothing is applied until you approve it" [2].
- **dbt self-healing guides** and a mid-2026 reference architecture for self-healing pipelines describe agents that propose and apply repairs [3, 4]. The architecture's safeguards are allowlisted playbooks, confidence gates, human approval and re-running the checks that detected the failure. It describes **no data comparison before a fix is applied** [4].

## 2. Fixes that pass today's checks are often wrong

- **Patches that pass the tests.** About 11% of "solved" SWE-bench issues are solved incorrectly, inflating resolution rates by 6.4 points on average. A differential test that compares each patch with the developer's own patch flags 29.6% of passing patches as behaving differently (PatchDiff, ICSE 2026) [5].
- **SQL that runs but is wrong.** In one model's erroneous text-to-SQL outputs, 98.7–98.8% of errors were *semantic*: the SQL runs and returns a wrong answer. Six LLMs asked to detect these errors averaged 75.16% accuracy [6].
- **Automatic patch-correctness checkers don't help in practice.** Across two datasets, random selection "outperforms all state-of-the-art" patch overfitting detectors "for 71% to 96% of the cases" [7].
- **The assistant study in this repository found the same problem:**
  - 7 of 36 AI-assistant repairs to data jobs changed output on inputs the job already handled;
  - all 7 passed "the job runs" and a regression test on the sample data ([`study/README.md`](../study/README.md)).

## 3. What exists, and the gap

| Approach | What it checks | Why it misses an agent's wrong fix |
|---|---|---|
| Run the fix on real data in a sandbox, then a human reviews it [1, 2] | The fix runs and gives plausible numbers on today's data | A NULL, a duplicate key or a new format that isn't in today's data is never exercised *(inference)* |
| Data diff: Datafold, Recce [8, 9] | Row, column and value differences between two tables, on existing data | Same blind spot: it compares the data you have, not the inputs that will break the logic later *(inference)* |
| dbt unit tests [10] | Model logic on mocked rows with expected outputs | People must write the mock rows and the expected results, "up to 5 hours per complex model" at Docusign, and keep them current |
| SQL equivalence checkers, e.g. VeriEQL [11] | Bounded equivalence of two queries, with counterexample databases | A repair is meant to change behaviour on the incident input, so "equivalent" is the wrong question. These are research tools tied to a modelled subset of SQL *(inference)* |
| Test-data generation for grading, e.g. XData [12] | Datasets that tell a query apart from its mutants | Needs a correct reference query, which doesn't exist when an agent repairs production code |
| PatchDiff [5] | Behaviour of an agent's patch against the developer's patch | Needs the developer's patch (an oracle) |

**The gap** *(inference)*: there is no check that needs no reference answer and that tells a reviewer whether an agent's change does both of these:
1. it handles the input that broke the job;
2. it gives the same result as before on every input the job already handled, including inputs that aren't in today's data, such as NULLs, duplicate keys, empty tables, extra columns, unusual formats and boundary numbers.

fixwitness 0.4–0.5 does this for scripts that read and write CSV files. Version 0.6 extends it to SQL queries and dbt models, where the agents above make their changes.

## Sources

1. Snowflake, *The Path to Autonomous Data Engineering: Fixing Data Pipeline Failures with AI*. https://www.snowflake.com/en/blog/ai-agent-fixes-data-pipeline-failures/
2. Databricks, *Introducing Genie ZeroOps*, 16 June 2026. https://databricks.com/blog/introducing-genie-zeroops
3. Paradime, *Autonomous dbt pipelines: implementing self-healing AI agents*. https://www.paradime.io/guides/dbt-self-healing-pipeline-ai-agents
4. Eshun et al., *Agentic Self-Healing for Data & AI Pipelines: An Affordable Vendor-Agnostic Architecture using Open-Source Software*, arXiv:2608.01955. https://arxiv.org/pdf/2608.01955
5. Wang, Pradel, Liu, *Are "Solved Issues" in SWE-bench Really Solved Correctly? An Empirical Study*, ICSE 2026, arXiv:2503.15223. https://arxiv.org/html/2503.15223v2
6. Liu et al., *NL2SQL-BUGs: A Benchmark for Detecting Semantic Errors in NL2SQL Translation*, arXiv:2503.11984. https://arxiv.org/pdf/2503.11984
7. Williams et al., *Unveiling Practical Shortcomings of Patch Overfitting Detection Techniques*, arXiv:2603.11262. https://arxiv.org/html/2603.11262v1
8. Datafold, *What is data diff*. https://docs.datafold.com/data-diff/what-is-data-diff
9. Recce, *The data-validation toolkit for enhanced dbt PR review*. https://github.com/DataRecce/recce
10. dbt Labs, *AI-assisted analytics engineering: Docusign's framework for scaling dbt unit testing*, edited 29 October 2026. https://www.getdbt.com/blog/ai-assisted-analytics-engineering-docusign-s-framework-for-scaling-dbt-unit-testing
11. He, Zhao, Wang, Wang, *VeriEQL: Bounded Equivalence Verification for Complex SQL Queries with Integrity Constraints*, arXiv:2403.03193. https://arxiv.org/abs/2403.03193
12. Chandra et al., *Data Generation for Testing and Grading SQL Queries*, VLDB Journal, arXiv:1411.6704. https://arxiv.org/abs/1411.6704
