-- label: wrong
-- pattern: case-insensitive match added: 'PAID' and 'Paid' now count as paid
select c.region, sum(o.amount) as revenue, count(*) as orders
from orders o
join customers c on c.customer_id = o.customer_id
where lower(o.status) = 'paid'
group by c.region
