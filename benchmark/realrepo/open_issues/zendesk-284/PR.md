# Pull request text for fivetran/dbt_zendesk (draft, not submitted)

**Title:** Fix `unreplied_ticket_count` and `unreplied_unsolved_ticket_count` always 0 in `zendesk__ticket_summary`

---

Resolves #284

### Please provide your name and company

Rishab Batra (independent contributor)

### Describe what this PR changes and how it addresses the linked issue or feature request.

`zendesk__ticket_summary` counts unreplied tickets with `total_agent_replies < 0`. Upstream,
`zendesk__ticket_metrics` sets `total_agent_replies` to `coalesce(ticket_comments.count_agent_replies, 0)`,
so it is never negative and both counts are always 0.

This PR:

- counts tickets where `total_agent_replies = 0` in `unreplied_ticket_count` and
  `unreplied_unsolved_ticket_count` (`models/zendesk__ticket_summary.sql`, two lines);
- adds an integrity test, `integration_tests/tests/integrity/ticket_summary_unreplied_count_match.sql`
  (enabled with `fivetran_validation_tests_enabled`, like the other integrity tests), that checks
  both counts against `zendesk__ticket_metrics` for each `source_relation`.

Suggested CHANGELOG entry:

```
## Bug Fix
- Fixes `unreplied_ticket_count` and `unreplied_unsolved_ticket_count` in `zendesk__ticket_summary`, which were always 0: they now count tickets with no agent reply (`total_agent_replies = 0`). Values change for every connection that has unreplied tickets.

## Under the Hood
- Adds the `ticket_summary_unreplied_count_match` integrity test.
```

### How did you validate the changes introduced within this PR, and what warehouse did you use for testing?

On DuckDB, with the integration-test seeds (dbt-core and dbt-duckdb, latest releases):

1. **The bug reproduces.** On `main` (c5f2cfa) with only the new integrity test added,
   `dbt seed`, `dbt run --select +zendesk__ticket_summary` and
   `dbt test --select ticket_summary_unreplied_count_match --vars '{fivetran_validation_tests_enabled: true}'`:
   the test fails.
2. **The fix works.** With this PR, the same commands pass.
3. **Nothing else changes.** [fixwitness](https://github.com/batrarishab14/fixwitness), run with
   `--expect-change zendesk__ticket_summary.unreplied_ticket_count,zendesk__ticket_summary.unreplied_unsolved_ticket_count`,
   builds both versions on the seeds and compares `zendesk__ticket_summary` on 293 generated
   inputs (edge cases built from the seeds: NULLs, repeated rows, boundary times, tickets linked to
   their comments). Of the 283 inputs both versions could run, only those two columns changed, on
   272 of them (on the seed data, `unreplied_ticket_count` goes from 0 to 3); every other column is
   identical on all 283.

The commands, logs and proof are in https://github.com/batrarishab14/fixwitness/tree/dev-0.6/benchmark/realrepo/open_issues/zendesk-284 (evidence run in CI, 24 November 2026).
