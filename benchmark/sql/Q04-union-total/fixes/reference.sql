-- label: correct
-- pattern: sum of per-channel sums (NULL when both are empty, like the original)
select sum(s) as total
from (
    select sum(amount) as s from online_orders
    union all
    select sum(amount) as s from store_orders
) t
