-- Gold layer: Revenue aggregated by nation and year
SELECT
    n.n_name AS nation,
    EXTRACT(YEAR FROM o.o_orderdate) AS order_year,
    COUNT(DISTINCT o.o_orderkey) AS total_orders,
    SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue,
    AVG(l.l_discount) AS avg_discount
FROM {{ ref('silver_orders') }} o
JOIN {{ ref('silver_lineitem') }} l ON o.o_orderkey = l.l_orderkey
JOIN {{ ref('silver_customer') }} c ON o.o_custkey = c.c_custkey
JOIN {{ source('source', 'nation') }} n ON c.c_nationkey = n.n_nationkey
GROUP BY n.n_name, EXTRACT(YEAR FROM o.o_orderdate)
ORDER BY nation, order_year
