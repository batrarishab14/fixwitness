-- label: wrong
-- pattern: NOT IN with a subquery: one NULL in blocked.customer_id makes it return no rows
select c.customer_id, c.name
from customers c
where c.customer_id not in (select customer_id from blocked)
