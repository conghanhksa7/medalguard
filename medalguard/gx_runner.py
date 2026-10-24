"""Post-transform Great Expectations (C2) validation runner on Silver layer."""
import duckdb


def run_gx_silver_suite(db_path: str) -> tuple[bool, list[dict]]:
    """Run Great Expectations equivalent expectation suite on Silver tables."""
    con = duckdb.connect(db_path, read_only=True)
    violations = []

    checks = [
        # silver_orders expectations
        ("ExpectColumnValuesToNotBeNull(o_orderkey)",
         "SELECT COUNT(*) FROM silver.silver_orders WHERE o_orderkey IS NULL"),
        ("ExpectColumnValuesToBeUnique(o_orderkey)",
         "SELECT COUNT(*) - COUNT(DISTINCT o_orderkey) FROM silver.silver_orders WHERE o_orderkey IS NOT NULL"),
        ("ExpectColumnValuesToNotBeNull(o_custkey)",
         "SELECT COUNT(*) FROM silver.silver_orders WHERE o_custkey IS NULL"),
        ("ExpectColumnValuesToBeInSet(o_orderstatus, ['O','F','P'])",
         "SELECT COUNT(*) FROM silver.silver_orders WHERE o_orderstatus IS NOT NULL AND o_orderstatus NOT IN ('O','F','P')"),
        ("ExpectColumnValuesToBeBetween(o_totalprice, min=0)",
         "SELECT COUNT(*) FROM silver.silver_orders WHERE o_totalprice < 0"),
        # silver_lineitem expectations
        ("ExpectColumnValuesToNotBeNull(l_orderkey)",
         "SELECT COUNT(*) FROM silver.silver_lineitem WHERE l_orderkey IS NULL"),
        ("ExpectColumnValuesToBeBetween(l_quantity, 1, 50)",
         "SELECT COUNT(*) FROM silver.silver_lineitem WHERE l_quantity < 1 OR l_quantity > 50"),
        ("ExpectColumnValuesToBeBetween(l_extendedprice, min=0)",
         "SELECT COUNT(*) FROM silver.silver_lineitem WHERE l_extendedprice < 0"),
        ("ExpectColumnValuesToBeBetween(l_discount, 0.0, 1.00)",
         "SELECT COUNT(*) FROM silver.silver_lineitem WHERE l_discount < 0.0 OR l_discount > 1.00"),
        ("ExpectColumnValuesToBeBetween(l_tax, 0.0, 0.08)",
         "SELECT COUNT(*) FROM silver.silver_lineitem WHERE l_tax < 0.0 OR l_tax > 0.08"),
    ]

    for exp_name, sql in checks:
        try:
            bad_cnt = con.execute(sql).fetchone()[0]
            if bad_cnt and bad_cnt > 0:
                violations.append({
                    "expectation": exp_name,
                    "unexpected_count": int(bad_cnt),
                })
        except Exception as e:
            violations.append({
                "expectation": exp_name,
                "error": str(e),
            })

    con.close()
    return (len(violations) > 0), violations
