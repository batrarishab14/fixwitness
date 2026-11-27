# Exercise-check validation on real packages

Runs `fixwitness.exercise.assess` on the real changed model SQL and real integration-test seeds of the study's
candidates (seeds only, first 200 rows; not the full generated cases).

    git clone --quiet --no-checkout --filter=blob:none https://github.com/fivetran/dbt_quickbooks qb
    python3 benchmark/realrepo/exercise_validation/sweep.py dbt_quickbooks qb

Result on 27 Nov 2026 (dbt_quickbooks): v0.5.3 flagged (no Accounts Payable/Receivable/UndepositedFunds seed rows);
v0.9.1 flagged on `credit` (probably a seeds-only artifact); v0.12.2, v0.14.1, v1.6.2, v1.9.2 not flagged;
refactor v1.8.1 not flagged. Other packages not yet run.
