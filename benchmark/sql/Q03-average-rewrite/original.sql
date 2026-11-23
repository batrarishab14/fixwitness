select product_id, avg(stars) as avg_stars
from ratings
group by product_id
