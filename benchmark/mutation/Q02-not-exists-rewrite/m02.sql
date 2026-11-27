select c.customer_id, c.name
from customers c
where not exists (select distinct 1 from blocked b where b.customer_id = c.customer_id)
