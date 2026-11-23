# Agent fixes

Put each agent's answer to `cases/<case-id>/PROMPT.md` here, unchanged:

```
agents/<agent-name>/<case-id>/<any-name>.py   (or .sh)
```

For example: `agents/claude-code-2026-11/I01-thousands-separator/load.py`.

Then run `python3 benchmark/run_bench.py`. Keep a note of the agent, model, version and date for each folder.

The folders here (`chatgpt-r1`, `claude-r1`, `copilot-r1`, `gemini-r1`) are the assistant study of 20 November 2026; see [`../../study/`](../../study/README.md).
