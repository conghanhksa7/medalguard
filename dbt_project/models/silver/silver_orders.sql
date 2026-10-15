-- Silver layer: Cleaned and typed orders
-- NOTE: NO WHERE clause filtering. Enforcement is handled by contracts / GX / MedalGuard.
SELECT
    o_orderkey,
    o_custkey,
    o_orderstatus,
    CAST(o_totalprice AS DOUBLE) AS o_totalprice,
    CAST(o_orderdate AS DATE) AS o_orderdate,
    o_orderpriority,
    o_clerk,
    o_shippriority
FROM {{ ref('bronze_orders') }}
