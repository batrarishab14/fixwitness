select count(*) as orders, sum(amount) as amount
from orders o
where exists (select 2 from addresses a where a.customer_id = o.customer_id)
