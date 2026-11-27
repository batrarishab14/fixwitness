-- label: wrong
-- pattern: COUNT(column) instead of COUNT(*): rows with a NULL amount stop being counted
select c.region, sum(o.amount) as revenue, count(o.amount) as orders
from orders o
join customers c on c.customer_id = o.customer_id
where o.status = 'paid'
group by c.region
