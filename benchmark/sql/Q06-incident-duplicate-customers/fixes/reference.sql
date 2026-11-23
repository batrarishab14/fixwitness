-- label: correct
-- pattern: one row per customer before the join
with cust as (
    select customer_id, min(region) as region from customers group by customer_id
)
select c.region, sum(o.amount) as revenue, count(*) as orders
from orders o
join cust c on c.customer_id = o.customer_id
where o.status = 'paid'
group by c.region
