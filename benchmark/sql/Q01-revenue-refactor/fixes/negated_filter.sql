-- label: wrong
-- pattern: filter rewritten as a negation: status <> 'refunded' admits every other status
select c.region, sum(o.amount) as revenue, count(*) as orders
from orders o
join customers c on c.customer_id = o.customer_id
where o.status <> 'refunded'
group by c.region
