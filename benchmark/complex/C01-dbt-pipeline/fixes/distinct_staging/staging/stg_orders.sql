select distinct order_id, customer_id, amount
from {{ source('shop', 'orders') }}
where status = 'paid'
