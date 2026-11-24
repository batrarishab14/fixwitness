-- label: wrong
-- pattern: COUNT_IF replaced by COUNT(*) over a filtered join (unpaid-only regions disappear)
select c.region,
       sum(o.amount) as revenue,
       count(*) as paid_orders
from analytics.raw.orders o
join analytics.raw.customers c on c.customer_id = o.customer_id
where o.status = 'paid'
group by c.region
