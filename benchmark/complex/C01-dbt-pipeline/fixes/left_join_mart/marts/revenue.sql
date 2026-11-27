{{ config(materialized='table') }}
select c.region, sum(o.amount) as revenue, count(*) as orders
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c on c.customer_id = o.customer_id
group by c.region
