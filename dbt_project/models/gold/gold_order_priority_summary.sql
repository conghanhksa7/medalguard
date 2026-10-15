-- Gold layer: Order counts and revenue by priority and status
SELECT
    o.o_orderpriority,
    o.o_orderstatus,
    COUNT(*) AS order_count,
    SUM(o.o_totalprice) AS total_value,
    AVG(o.o_totalprice) AS avg_order_value
FROM {{ ref('silver_orders') }} o
GROUP BY o.o_orderpriority, o.o_orderstatus
ORDER BY o.o_orderpriority, o.o_orderstatus
