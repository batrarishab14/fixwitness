select count(*) as orders, avg(amount) as amount
from orders o
where exists (select 1 from addresses a where a.customer_id = o.customer_id)
