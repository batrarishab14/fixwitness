## fixwitness: FAIL (1 check)

| Changed | Checked as | Result | Why |
|---|---|---|---|
| `integration_tests (dbt project)` | dbt | **FAIL** | If the file is tables as given, in `shopify__daily_shop`, columns `count_fulfillment_attempted_delivery`, `count_fulfillment_delayed`, `count_fulfillment_delivered`, `count_fulfillment_failure`, `count_fulfillment_in_transit`, `count_fulfillment_out_for_delivery`, `count_fulfillment_ready_for_pickup`, `count_fulfillment_picked_up`, `count_fulfillment_label_printed`, `count_fulfillment_label_purchased`, `count_fulfillment_confirmed` appear. |

Not checked: `CHANGELOG.md` (documentation); `docs/catalog.json` (not code); `docs/index.html` (not code); `docs/manifest.json` (not code); `docs/run_results.json` (new file: there is no original to compare)

---

### `integration_tests (dbt project)`


`integration_tests`: commit `903e5629b4af` (original) vs working tree (fix); changed: `.quickstart/quickstart.yml`, `CHANGELOG.md`, `dbt_project.yml`, `docs/catalog.json`, `docs/index.html` and 9 more. dbt project: changed `shopify__collection_metafields`, `shopify__customer_metafields`, `shopify__customers`, `shopify__daily_shop`, `shopify__order_metafields`, `shopify__product_image_metafields`, `shopify__product_metafields`, `shopify__product_variant_metafields`, `shopify__shop_metafields`, `stg_shopify__fulfillment_event`, `stg_shopify__fulfillment_event_tmp`; compared `shopify__customer_cohorts`, `shopify__customers`, `shopify__daily_shop`; SQL on warehouse; tables `shopify_order_adjustment_data` (shopify_order_adjustment_data.csv), `shopify_refund_data` (shopify_refund_data.csv), `shopify_fulfillment_data` (shopify_fulfillment_data.csv), `shopify_order_url_tag_data` (shopify_order_url_tag_data.csv), `shopify_order_shipping_tax_line_data` (shopify_order_shipping_tax_line_data.csv), `shopify_shop_data` (shopify_shop_data.csv), `shopify_product_variant_data` (shopify_product_variant_data.csv), `shopify_order_line_refund_data` (shopify_order_line_refund_data.csv), `shopify_abandoned_checkout_data` (shopify_abandoned_checkout_data.csv), `shopify_order_data` (shopify_order_data.csv), `shopify_order_discount_code_data` (shopify_order_discount_code_data.csv), `shopify_order_tag_data` (shopify_order_tag_data.csv), `shopify_tax_line_data` (shopify_tax_line_data.csv), `shopify_customer_data` (shopify_customer_data.csv), `shopify_order_shipping_line_data` (shopify_order_shipping_line_data.csv), `shopify_fulfillment_event_data` (shopify_fulfillment_event_data.csv), `shopify_transaction_data` (shopify_transaction_data.csv), `shopify_tender_transaction_data` (shopify_tender_transaction_data.csv), `shopify_order_line_data` (shopify_order_line_data.csv), `shopify_customer_tag_data` (shopify_customer_tag_data.csv)

| Check | Result |
|---|---|
| Security | not checked (attack payloads turned off) |
| Data unchanged | FAIL: 0 of 1 comparable valid inputs give the same output |
| Not comparable | 295 valid inputs made the original fail too |
| Needs review | 0 of 4 inputs in review categories (inputs that break your dbt tests (stg_shopify__fulfillment: accepted_values(status); stg_shopify__fulfillment: not_null(fulfillment_id))) differ |

**Why:** the fix changes output on 1 valid inputs.

- Note: 295 valid inputs could not be compared because the original failed on them

**What could go wrong:**

- **Values change.** If the file is tables as given, in `shopify__daily_shop`, columns `count_fulfillment_attempted_delivery`, `count_fulfillment_delayed`, `count_fulfillment_delivered`, `count_fulfillment_failure`, `count_fulfillment_in_transit`, `count_fulfillment_out_for_delivery`, `count_fulfillment_ready_for_pickup`, `count_fulfillment_picked_up`, `count_fulfillment_label_printed`, `count_fulfillment_label_purchased`, `count_fulfillment_confirmed` appear.
  - case 000: `file-structure` input '<tables as given>' in `None` (changed)
  - shopify__daily_shop: header: [['date_day', 'shop_id', 'name', 'domain', 'is_deleted', 'currency', 'enabled_presentment_currencies', 'iana_timezone', 'created_at', 'source_relation', 'count_orders',...

Proof ID `d41d268aa09a5aea` · re-check with `fixwitness replay /home/runner/work/fixwitness/fixwitness/study-out/runs/shopify@v0.13.2/out/integration_tests_dbt_project/proof.json`
