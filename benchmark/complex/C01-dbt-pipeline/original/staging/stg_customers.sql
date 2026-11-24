select customer_id, region from {{ source('shop', 'customers') }}
