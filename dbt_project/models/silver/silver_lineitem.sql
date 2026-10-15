-- Silver layer: Cleaned and typed lineitem
-- NOTE: NO WHERE clause filtering. Enforcement is handled by contracts / GX / MedalGuard.
SELECT
    l_orderkey,
    l_partkey,
    l_suppkey,
    l_linenumber,
    CAST(l_quantity AS DOUBLE) AS l_quantity,
    CAST(l_extendedprice AS DOUBLE) AS l_extendedprice,
    CAST(l_discount AS DOUBLE) AS l_discount,
    CAST(l_tax AS DOUBLE) AS l_tax,
    l_returnflag,
    l_linestatus,
    CAST(l_shipdate AS DATE) AS l_shipdate,
    CAST(l_commitdate AS DATE) AS l_commitdate,
    CAST(l_receiptdate AS DATE) AS l_receiptdate,
    l_shipinstruct,
    l_shipmode,
    l_comment
FROM {{ ref('bronze_lineitem') }}
