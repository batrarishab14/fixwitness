# Bug zoo: changes that pass on today's data

Each change below gives exactly the same result as the original on the sample tables, so a test run or a data diff on today's data passes it. Each one gives a different answer as soon as the data has one ordinary property it doesn't have today. The sentence under each is what fixwitness reports, with the smallest input that shows it.

All eight are in the [playground](playground/standalone.html) (open the page, pick one, press Check). The sample tables:

```
orders                                   customers
order_id,customer_id,amount,status       customer_id,name,region
1,10,12.50,paid                          10,Acme Ltd,east
2,10,300.75,paid                         11,Globex,west
3,11,99.99,refunded                      12,Initech,east
4,12,5.25,paid
```

| # | The change | When it differs | What fixwitness reports |
|---|---|---|---|
| 1 | `count(*)` → `count(o.amount)` | an order with no amount | If an orders row has an empty amount, orders for 'east' changes from 1 to 0. |
| 2 | `NOT EXISTS (...)` → `NOT IN (select customer_id ...)` | an order with no customer | If an orders row has an empty customer_id, the result has 0 rows instead of 3. |
| 3 | `join` → `left join` | an order whose customer is unknown | If an orders row has an empty customer_id, the result has 1 row instead of 0. |
| 4 | `status = 'paid'` → `lower(status) = 'paid'` | a status in capitals | If orders.status is written in another case ('PAID'), paid_orders changes from 0 to 1. |
| 5 | `union all` → `union` | two orders with the same amount | If an orders row appears twice, total changes from 25 to 12.5. |
| 6 | `avg(amount)` → `avg(coalesce(amount, 0))` | an order with no amount | If an orders row has an empty amount, avg_amount for 10 changes from NULL to 0. |
| 7 | `round(sum(amount), 2)` → `sum(round(amount, 2))` | two orders of one region with sub-cent amounts | If two orders rows of the same group have amount = 0.005 and 0.005, revenue for 'east' changes from 0.01 to 0.02. |
| 8 | `from orders` → `from (select distinct * from orders)` | the same order loaded twice | If an orders row appears twice, revenue for 'east' changes from 25 to 12.5. |

A ninth preset in the playground, a CTE rewrite of query 1, gives the same results on all 71 variations, as it should.

The same mistakes happen outside SQL:

| SQL | pandas | polars | Python on JSON |
|---|---|---|---|
| `count(*)` → `count(col)` | `size()` → `count()` | `pl.len()` → `pl.col(c).count()` | |
| `NULL` treated as 0 | `fillna(0)` before `mean()` | `fill_null(0)` | `e.get("amount", 0)` |
| case-insensitive filter | `.str.lower() ==` | `.str.to_lowercase() ==` | `.lower() ==` |
| DISTINCT added | `drop_duplicates()` | `unique()` | `set()` over records |
| group with a NULL key | `groupby` drops it | `group_by` keeps it | `dict` keeps `None` |
| strict key | | | `e["status"]` instead of `e.get("status")` |

The pandas, polars and JSON versions are in [`benchmark/complex/`](../benchmark/complex/).

These sentences come from the playground's engine (a JavaScript port of fixwitness's SQL cases, run on SQLite in the browser), run on 24 November 2026. The command-line tool reports the same differences, and checks more kinds of input.
