## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If a `workday_worker_history_data` row has an empty `_fivetran_start`, in `workday__employee_overview`, the output has 1 row instead of 0; a new row for '7687e33f1595019b167eba8cd456b424' appears. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `7f0441e1ac8e` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 8 more. dbt project: changed `stg_workday__personal_information`, `stg_workday__worker`, `stg_workday__worker_position`, `stg_workday__worker_position_organization`, `workday__employee_overview`; compared `workday__employee_overview`, `workday__organization_overview`; SQL on warehouse; tables `workday_organization_role_data` (workday_organization_role_data.csv), `workday_personal_information_history_data` (workday_personal_information_history_data.csv), `workday_organization_data` (workday_organization_data.csv), `workday_worker_history_data` (workday_worker_history_data.csv), `workday_worker_position_history_data` (workday_worker_position_history_data.csv), `workday_military_service_data` (workday_military_service_data.csv), `workday_person_contact_email_address_data` (workday_person_contact_email_address_data.csv), `workday_personal_information_ethnicity_data` (workday_personal_information_ethnicity_data.csv), `workday_person_name_data` (workday_person_name_data.csv), `workday_worker_position_organization_history_data` (workday_worker_position_organization_history_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 285 of 300 comparable valid inputs give the same output |

**Why:** the fix changes output on 15 valid inputs.

**What could go wrong:**

- **Rows added or lost.** If a `workday_worker_history_data` row has an empty `_fivetran_start`, in `workday__employee_overview`, the output has 1 row instead of 0; a new row for '7687e33f1595019b167eba8cd456b424' appears.
  - case 136: `empty` input '' in `workday_worker_history_data._fivetran_start` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row count: 2 -> 3
  - workday__employee_overview: row 2, worker_id: '7687e33f159501c831d2f28cd4560225' -> '7687e33f1595019b167eba8cd456b424'
- **Rows added or lost.** If a `workday_worker_history_data` row has an empty `_fivetran_end`, in `workday__employee_overview`, the output has 1 row instead of 0; a new row for '7687e33f1595019b167eba8cd456b424' appears.
  - case 139: `empty` input '' in `workday_worker_history_data._fivetran_end` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row count: 2 -> 3
  - workday__employee_overview: row 2, worker_id: '7687e33f159501c831d2f28cd4560225' -> '7687e33f1595019b167eba8cd456b424'
- **Rows added or lost.** If every `_fivetran_start` in `workday_worker_history_data` is empty (NULL), in `workday__employee_overview`, the output has 1 row instead of 0; a new row for '7687e33f159501c831d2f28cd4560225' appears.
  - case 219: `null-column` input '<all NULL>' in `workday_worker_history_data._fivetran_start` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row count: 0 -> 3
- **Rows added or lost.** If every `_fivetran_end` in `workday_worker_history_data` is empty (NULL), in `workday__employee_overview`, the output has 1 row instead of 0; a new row for '7687e33f159501c831d2f28cd4560225' appears.
  - case 220: `null-column` input '<all NULL>' in `workday_worker_history_data._fivetran_end` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row count: 0 -> 3
- **Rows added or lost.** If a `workday_worker_history_data` row has `_fivetran_active` set to 'false', in `workday__employee_overview`, the output has 0 rows instead of 1; the row for '7687e33f1595019b167eba8cd456b424' is missing.
  - case 232: `flip` input 'false' in `workday_worker_history_data._fivetran_active` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row count: 3 -> 2
  - workday__employee_overview: row 2, worker_id: '7687e33f1595019b167eba8cd456b424' -> '7687e33f159501c831d2f28cd4560225'
- **Values change.** If a `workday_worker_position_history_data` row has an empty `_fivetran_start`, in `workday__employee_overview`, `position_id` for '7687e33f1595019b167eba8cd456b424' changes from empty to 'b6704e966cc4013c8be899b8a553f6bb' (and 11 more cells).
  - case 249: `empty` input '' in `workday_worker_position_history_data._fivetran_start` (changed); input shrunk to the rows that show it
  - workday__employee_overview: row 3, position_id: '' -> 'b6704e966cc4013c8be899b8a553f6bb'
  - workday__employee_overview: row 3, business_title: '' -> 'true'
- **Values change.** If a `workday_worker_position_history_data` row has an empty `_fivetran_end`, in `workday__employee_overview`, `position_id` for '7687e33f1595019b167eba8cd456b424' changes from empty to 'b6704e966cc4013c8be899b8a553f6bb' (and 11 more cells).
  - case 252: `empty` input '' in `workday_worker_position_history_data._fivetran_end` (changed)
  - workday__employee_overview: row 3, position_id: '' -> 'b6704e966cc4013c8be899b8a553f6bb'
  - workday__employee_overview: row 3, business_title: '' -> 'true'
- **Values change.** If every `_fivetran_start` in `workday_worker_position_history_data` is empty (NULL), in `workday__employee_overview`, `position_id` for '7687e33f1595017a1330268bd456a822' changes from empty to 'd0e0ae2f7be848cb8f19178750a21564' (and 33 more cells).
  - case 263: `null-column` input '<all NULL>' in `workday_worker_position_history_data._fivetran_start` (changed)
  - workday__employee_overview: row 2, position_id: '' -> 'd0e0ae2f7be848cb8f19178750a21564'
  - workday__employee_overview: row 2, business_title: '' -> 'true'

Proof ID `6ef5a938b34e6c24` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/workday@v0.1.1/out/integration_tests_dbt_project/proof.json`
