-- label: wrong
-- pattern: = changed to ILIKE (case-insensitive match)
select c.region,
       sum(iff(o.status ilike 'paid', o.amount, 0)) as revenue,
       count_if(o.status ilike 'paid') as paid_orders
from analytics.raw.orders o
join analytics.raw.customers c on c.customer_id = o.customer_id
group by c.region
