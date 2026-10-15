-- Silver layer: Cleaned and typed customer
-- NOTE: NO WHERE clause filtering. Enforcement is handled by contracts / GX / MedalGuard.
SELECT
    c_custkey,
    c_name,
    c_address,
    c_nationkey,
    c_phone,
    CAST(c_acctbal AS DOUBLE) AS c_acctbal,
    c_mktsegment,
    c_comment
FROM {{ ref('bronze_customer') }}
