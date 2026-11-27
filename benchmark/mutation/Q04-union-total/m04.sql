select sum(amount) as total
from (
 select amount from online_orders
 union all
 select distinct amount from store_orders
) t
