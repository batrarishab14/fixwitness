select order_id, customer_id, amount, status from {{ source('shop', 'orders') }}
