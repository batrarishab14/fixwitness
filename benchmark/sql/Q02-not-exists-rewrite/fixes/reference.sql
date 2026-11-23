-- label: correct
-- pattern: anti-join with LEFT JOIN ... IS NULL
select c.customer_id, c.name
from customers c
left join blocked b on b.customer_id = c.customer_id
where b.customer_id is null
