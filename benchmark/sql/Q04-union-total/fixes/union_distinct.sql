-- label: wrong
-- pattern: UNION instead of UNION ALL: equal amounts are counted once
select sum(amount) as total
from (
    select amount from online_orders
    union
    select amount from store_orders
) t
