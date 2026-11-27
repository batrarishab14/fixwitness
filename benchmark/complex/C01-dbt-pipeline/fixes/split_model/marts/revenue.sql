{{ config(materialized='table') }}
select c.region, sum(o.amount) as revenue, count(*) as orders
from {{ ref('paid_orders') }} o
join {{ ref('stg_customers') }} c on c.customer_id = o.customer_id
group by c.region
