## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is sample as given, in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `25153c1e9ef1` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `docs/run_results.json` and 4 more. dbt project: changed `stg_shopify__abandoned_checkout_discount_code`; compared `stg_shopify__abandoned_checkout_discount_code`; SQL on warehouse; tables `shopify_abandoned_checkout_discount_code_data` (shopify_abandoned_checkout_discount_code_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 237 comparable valid inputs give the same output |
| Not comparable | 49 valid inputs made the original fail too |

**Why:** the fix changes output on 237 valid inputs.

- Note: 49 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is sample as given, in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 000: `file-structure` input '<sample as given>' in `shopify_abandoned_checkout_discount_code_data` (changed)
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If the file is header only, in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 001: `file-structure` input '<header only>' in `shopify_abandoned_checkout_discount_code_data` (changed)
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If the input has another column layout (<extra column at the end>), in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 002: `schema` input '<extra column at the end>' in `shopify_abandoned_checkout_discount_code_data` (changed); input shrunk to the rows that show it
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If the input has another column layout (<extra column at the start>), in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 003: `schema` input '<extra column at the start>' in `shopify_abandoned_checkout_discount_code_data` (changed); input shrunk to the rows that show it
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If the input has another column layout (<columns in reverse order>), in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 004: `schema` input '<columns in reverse order>' in `shopify_abandoned_checkout_discount_code_data` (changed); input shrunk to the rows that show it
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If the input has another column layout (<first column moved to the end>), in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 005: `schema` input '<first column moved to the end>' in `shopify_abandoned_checkout_discount_code_data` (changed); input shrunk to the rows that show it
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If `code` is 'a; "b"', in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 007: `delimiter-mix` input 'a; "b"' in `shopify_abandoned_checkout_discount_code_data.code` (changed)
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...
- **Values change.** If `type` is 'a; "b"', in `stg_shopify__abandoned_checkout_discount_code`, column `index` disappears.
  - case 008: `delimiter-mix` input 'a; "b"' in `shopify_abandoned_checkout_discount_code_data.type` (changed)
  - stg_shopify__abandoned_checkout_discount_code: header: [['checkout_id', 'code', 'discount_id', 'amount', 'type', 'created_at', 'updated_at', '_fivetran_synced', 'source_relation', 'index']] -> [['c...

Proof ID `f5ed15fb7d2e29f8` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/shopify_source@v0.8.1/out/integration_tests_dbt_project/proof.json`
