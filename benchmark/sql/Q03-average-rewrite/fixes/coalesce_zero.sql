-- label: wrong
-- pattern: NULL treated as 0: missing ratings become 0 stars
select product_id, avg(coalesce(stars, 0)) as avg_stars
from ratings
group by product_id
