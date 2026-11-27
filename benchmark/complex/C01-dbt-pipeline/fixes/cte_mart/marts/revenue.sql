{{ config(materialized='table') }}
with orders as (select * from {{ ref('stg_orders') }}),
     customers as (select * from {{ ref('stg_customers') }}),
     joined as (
         select customers.region, orders.amount
         from orders inner join customers using (customer_id)
     )
select region, sum(amount) as revenue, count(*) as orders
from joined
group by region
