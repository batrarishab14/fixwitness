## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `message_data` is 'a; "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs. |

Not checked: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md` (documentation); `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `be9ee6b7fdb0` (original) vs working tree (fix); changed: `.github/PULL_REQUEST_TEMPLATE/maintainer_pull_request_template.md`, `.github/workflows/auto-release.yml`, `.quickstart/quickstart.yml`, `CHANGELOG.md`, `dbt_project.yml` and 6 more. dbt project: changed `fivetran_platform__audit_user_activity`; compared `fivetran_platform__audit_user_activity`; SQL on warehouse; tables `user` (user.csv), `destination` (destination.csv), `log` (log.csv), `connector` (connector.csv), `destination_membership` (destination_membership.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 266 of 281 comparable valid inputs give the same output |
| Needs review | 0 of 19 inputs in review categories (inputs that break your dbt tests (stg_fivetran_platform__destination: unique(destination_id); stg_fivetran_platform__destination_membership: unique_combination_of_columns(destination_id, user_id); stg_fivetran_platform__log: unique_combination_of_columns(log_id, created_at); stg_fivetran_platform__user: not_null(user_id))) differ |

**Why:** the fix changes output on 15 valid inputs.

**What could go wrong:**

- **The job fails.** If `message_data` is 'a; "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 157: `delimiter-mix` input 'a; "b"' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is '"a"; b', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 159: `delimiter-mix` input '"a"; b' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: "a";...
- **The job fails.** If `message_data` is 'a;b;c', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 161: `delimiter-mix` input 'a;b;c' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is 'a	 "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 163: `delimiter-mix` input 'a\t "b"' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is '"a"	 b', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 165: `delimiter-mix` input '"a"\t b' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: "a"	 b
- **The job fails.** If `message_data` is 'a	b	c', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 167: `delimiter-mix` input 'a\tb\tc' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is 'a| "b"', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 169: `delimiter-mix` input 'a| "b"' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: a...
- **The job fails.** If `message_data` is '"a"| b', the fix fails (fixwitness.sqlrun: query failed: InvalidTextRepresentation: invalid input syntax for type json) while the original runs.
  - case 171: `delimiter-mix` input '"a"| b' in `log.message_data` (after-failed)
  - CONTEXT:  JSON data, line 1: "a"/...

Proof ID `90ded1825e6c3a74` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/fivetran_log@v1.4.1/out/integration_tests_dbt_project/proof.json`
