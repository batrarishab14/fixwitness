-- label: correct
-- pattern: semi-join written as IN (no fan-out)
select count(*) as orders, sum(amount) as amount
from orders o
where o.customer_id in (select customer_id from addresses)
