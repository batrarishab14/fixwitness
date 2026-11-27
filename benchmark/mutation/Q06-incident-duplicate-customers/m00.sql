select c.region, sum(o.amount) as revenue, count(*) as orders
from orders o
left join customers c on c.customer_id = o.customer_id
where o.status = 'paid'
group by c.region
