select count(*) as orders, sum(amount) as amount
from orders o
where exists (select distinct 1 from addresses a where a.customer_id = o.customer_id)
