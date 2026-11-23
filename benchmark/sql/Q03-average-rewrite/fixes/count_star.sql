-- label: wrong
-- pattern: COUNT(*) as the divisor: NULL ratings now pull the average down
select product_id, sum(stars) * 1.0 / count(*) as avg_stars
from ratings
group by product_id
