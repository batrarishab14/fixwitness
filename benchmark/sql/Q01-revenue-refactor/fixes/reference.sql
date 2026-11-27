-- label: correct
-- pattern: the filter moved into a CTE; same joins and aggregates
with paid as (
    select customer_id, amount from orders where status = 'paid'
)
select c.region, sum(p.amount) as revenue, count(*) as orders
from paid p
join customers c on c.customer_id = p.customer_id
group by c.region
