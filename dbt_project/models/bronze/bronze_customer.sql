-- Bronze layer: Raw ingestion from source (no transformation)
SELECT
    c_custkey,
    c_name,
    c_address,
    c_nationkey,
    c_phone,
    c_acctbal,
    c_mktsegment,
    c_comment
FROM {{ source('source', 'customer') }}
