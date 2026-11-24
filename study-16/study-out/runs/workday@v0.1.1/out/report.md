## fixwitness: INCONCLUSIVE (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | INCONCLUSIVE | no valid input could be compared (the original failed on all of them) |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `7f0441e1ac8e` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html`, `docs/manifest.json` and 8 more. dbt project: changed `stg_workday__personal_information`, `stg_workday__worker`, `stg_workday__worker_position`, `stg_workday__worker_position_organization`, `workday__employee_overview`; compared `workday__employee_overview`, `workday__organization_overview`; SQL on warehouse; tables `workday_organization_role_data` (workday_organization_role_data.csv), `workday_personal_information_history_data` (workday_personal_information_history_data.csv), `workday_organization_data` (workday_organization_data.csv), `workday_worker_history_data` (workday_worker_history_data.csv), `workday_worker_position_history_data` (workday_worker_position_history_data.csv), `workday_military_service_data` (workday_military_service_data.csv), `workday_person_contact_email_address_data` (workday_person_contact_email_address_data.csv), `workday_personal_information_ethnicity_data` (workday_personal_information_ethnicity_data.csv), `workday_person_name_data` (workday_person_name_data.csv), `workday_worker_position_organization_history_data` (workday_worker_position_organization_history_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 0 comparable valid inputs give the same output |
| Not comparable | 300 valid inputs made the original fail too |

**Why:** no valid input could be compared (the original failed on all of them).

- Note: the original failed on the sample itself: fixwitness.sqlrun: table workday_personal_information_history_data has an empty or repeated column name
- Note: 300 valid inputs could not be compared because the original failed on them

Proof ID `144d7764a61bf0cb` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/workday@v0.1.1/out/integration_tests_dbt_project/proof.json`
