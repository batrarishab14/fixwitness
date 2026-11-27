## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If `id` is the number 0, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/manifest.json` (not code)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `0f418b67cc03` (original) vs working tree (fix); changed: `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/manifest.json`, `integration_tests/ci/sample.profiles.yml` and 10 more. dbt project: changed `shopify__customer_metafields`, `shopify__order_metafields`, `shopify__product_image_metafields`, `shopify__product_variant_metafields`; compared `shopify__customer_metafields`, `shopify__order_metafields`, `shopify__product_image_metafields`, `shopify__product_variant_metafields`; SQL on warehouse; tables `shopify_metafield_data` (shopify_metafield_data.csv), `shopify_product_variant_data` (shopify_product_variant_data.csv), `shopify_order_data` (shopify_order_data.csv), `shopify_product_image_data` (shopify_product_image_data.csv), `shopify_customer_data` (shopify_customer_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 300 comparable valid inputs give the same output |

**Why:** the fix changes output on 300 valid inputs.

**What could go wrong:**

- **Values change.** If `id` is the number 0, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 000: `numeric-format` input '0' in `shopify_metafield_data.id` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If a `shopify_metafield_data` row has an empty `id`, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 001: `empty` input '' in `shopify_metafield_data.id` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If `id` repeats the value of another row (5445055), in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 002: `duplicate` input '5445055' in `shopify_metafield_data.id` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If two `shopify_metafield_data` rows of the same group have `id` = 9007199254740993 and 1, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 003: `pairs` input '9007199254740993 | 1' in `shopify_metafield_data.id` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If a `shopify_metafield_data` row has an empty `_fivetran_synced`, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 004: `empty` input '' in `shopify_metafield_data._fivetran_synced` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If `_fivetran_synced` repeats the value of another row ('2022-11-19 10:06:09.531000'), in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 005: `duplicate` input '2022-11-19 10:06:09.531000' in `shopify_metafield_data._fivetran_synced` (changed); input shrunk to the rows that show it
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If two `shopify_metafield_data` rows of the same group have `_fivetran_synced` = '2022-11-21 01:57:33.851000' and '2022-11-21 01:57:33.851000', in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 006: `pairs` input '2022-11-21 01:57:33.851000 | 2022-11-21 01:57:33.851000' in `shopify_metafield_data._fivetran_synced` (changed)
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...
- **Values change.** If a `shopify_metafield_data` row has an empty `created_at`, in `shopify__customer_metafields`, columns `metafield_star_wars_firstname`, `metafield_star_wars_fullname`, `metafield_star_wars_isjedi`, `metafield_star_wars_lastname` disappear.
  - case 007: `empty` input '' in `shopify_metafield_data.created_at` (changed)
  - shopify__customer_metafields: header: [['customer_id', 'email', 'first_name', 'last_name', 'orders_count', 'default_address_id', 'phone', 'account_state', 'is_tax_exempt', 'total_spent', 'is_verifi...
  - shopify__order_metafields: header: [['order_id', 'user_id', 'total_discounts', 'total_discounts_set', 'total_line_items_price', 'total_line_items_price_set', 'total_price', 'total_price_set', 'tota...

Proof ID `01c4de15cfeab0d5` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/shopify@v0.16.1/out/integration_tests_dbt_project/proof.json`
