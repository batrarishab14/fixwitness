# fixwitness 0.6: evaluation protocol (amends PROTOCOL_v0.5.md)

Written on 23 November 2026, **before any held-out task exists.**

## Why the protocol changed

`PROTOCOL_v0.5.md` planned to freeze 0.5.0 and evaluate it on new CSV tasks. Before that happened, research on where AI agents change data pipelines ([`docs/RESEARCH.md`](../docs/RESEARCH.md)) moved the main target to SQL queries and dbt models, and 0.6 adds them. The held-out evaluation therefore measures 0.6.0, on both kinds of task. No held-out task, assistant run or label existed when this amendment was written, so nothing has been seen that could bias it.

## Development results

These are reported as development, not evaluation:
- the 92 fixes in `benchmark/` (CSV scripts);
- the 17 changes in `benchmark/sql/`;
- the 36-fix assistant study in `study/`.

See `DEVLOG_v0.5.md` and `DEVLOG_v0.6.md`.

## Held-out evaluation (the number to publish)

1. **Freeze the tool:** tag `v0.6.0` (a GitHub release) before any held-out task is written.
2. **Write the tasks** and commit them before any assistant sees them, in the formats of `benchmark/cases/` and `benchmark/sql/`:
   - **10 CSV incident tasks**, none reusing a failure type of I01–I09;
   - **10 SQL tasks**, refactors or incidents, none reusing a pitfall from Q01–Q06.

   Each task has its sample data, an original, a task text, and for incidents the incident input and the expected output.
3. **Collect changes:** the author gives each task to AI assistants in fresh chats (12 chats planned) and saves every answer unchanged, with model and date, following `study/README.md`.
4. **Label before scoring:** every change is labelled correct or wrong by the task's rule: do what the task asks, and change nothing for any input the original handled. Every "wrong" label cites an input that reproduces the difference. The author approves the labels **before** fixwitness 0.6.0 is run on these changes.
5. **Score:** run the four checks (runs, same result on the sample, fixwitness, fixwitness + expected) with `pip install "git+https://github.com/batrarishab14/fixwitness@v0.6.0"`, and report every miss and every false alarm.

The tool is not changed between steps 1 and 5. A later change is a new version, evaluated on new held-out tasks.
