select product_id, sum(stars) as avg_stars
from ratings
group by product_id
