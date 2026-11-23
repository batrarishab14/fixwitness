-- label: correct
-- pattern: SUM over COUNT of the same column (both skip NULLs)
select product_id, sum(stars) * 1.0 / count(stars) as avg_stars
from ratings
group by product_id
