# Pull request text for fivetran/dbt_lever (draft, not submitted)

**Title:** Fix duplicate rows in `lever__interview_enhanced` for deleted feedback forms

---

Resolves #43

### Please provide your name and company

Rishab Batra (independent contributor)

### Describe what this PR changes and how it addresses the linked issue or feature request.

As described in #43, `int_lever__interview_feedback` filters deleted forms out of the
`feedback_form` CTE but still left joins every `interview_feedback` bridge row, so each deleted form
adds a row with a `NULL` `feedback_form_id`.

This PR follows the approach proposed in the issue:

- joins `interview_feedback` to the live (not deleted) feedback forms first, in a new
  `live_interview_feedback` CTE, then left joins `interview` to it. An interview with no live form
  keeps exactly one row, with a `NULL` form;
- restores the `dbt_utils.unique_combination_of_columns` test on `lever__interview_enhanced`
  (`source_relation`, `feedback_form_id`, `interview_id`) removed in 7829497;
- adds integration seed rows that link across tables: an interview with two deleted forms, an
  interview with one live and one deleted form, and the two interviews' opportunities (without
  them, the mart's inner join to `opportunity` drops the interviews and the bug can't show).

Suggested CHANGELOG entry:

```
## Bug Fix
- Fixes duplicate rows in `lever__interview_enhanced` when an interview has deleted feedback forms: links to deleted forms no longer add rows ([#43](https://github.com/fivetran/dbt_lever/issues/43)).

## Under the Hood
- Restores the uniqueness test on `lever__interview_enhanced` and adds integration seed rows that link interviews, feedback forms and opportunities.
```

Note: the fan-out when an opportunity has more than one application (#22) is not part of this PR.

### How did you validate the changes introduced within this PR, and what warehouse did you use for testing?

On DuckDB, with the integration-test seeds (dbt-core and dbt-duckdb, latest releases):

1. **The bug reproduces.** `main`'s model with the new seed rows fails the restored uniqueness test.
2. **The fix works.** With this PR, `dbt build --select +lever__interview_enhanced` passes.
3. **Found without the new seed rows.** [fixwitness](https://github.com/batrarishab14/fixwitness), run on
   the model change alone with `main`'s own seeds, links the seeds' keys across tables and reports
   the difference: {FINDING}. Proof ID `{PROOF}`.

The commands and logs are in {LINK}.
