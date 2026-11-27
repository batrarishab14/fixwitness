-- label: correct
-- pattern: IFF and COUNT_IF written as CASE expressions
select c.region,
       sum(case when o.status = 'paid' then o.amount else 0 end) as revenue,
       sum(case when o.status = 'paid' then 1 else 0 end) as paid_orders
from raw.orders as o
inner join raw.customers as c on o.customer_id = c.customer_id
group by c.region
