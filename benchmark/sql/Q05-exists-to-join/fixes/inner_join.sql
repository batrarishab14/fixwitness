-- label: wrong
-- pattern: join fan-out: a customer with two addresses doubles their orders
select count(*) as orders, sum(o.amount) as amount
from orders o
join addresses a on a.customer_id = o.customer_id
