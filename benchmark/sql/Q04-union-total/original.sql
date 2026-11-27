select sum(amount) as total
from (
    select amount from online_orders
    union all
    select amount from store_orders
) t
