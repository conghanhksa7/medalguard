"""MedalGuard Multi-Tier Lineage DAG & Root-Cause Diff Engine.

Provides:
1. Multi-tier Lakehouse Lineage DAG (source -> bronze -> silver -> gold) and downstream KPI impact analysis.
2. Root-cause diff analysis comparing expected contract specification vs actual lakehouse table state.
"""
from typing import Any
import duckdb
from .utils import parse_table_ref


# ---------------------------------------------------------------------------
# Multi-Tier Lineage Specification
# ---------------------------------------------------------------------------
LINEAGE_DAG = {
    "tables": {
        "orders": {
            "source": "source.orders",
            "bronze": "bronze.bronze_orders",
            "silver": "silver.silver_orders",
            "gold": [
                "gold.gold_revenue_by_nation",
                "gold.gold_order_priority_summary",
            ],
            "columns": {
                "o_orderkey": {
                    "role": "PRIMARY_KEY",
                    "silver": "silver_orders.o_orderkey",
                    "gold_joins": [
                        {"target": "silver_lineitem.l_orderkey", "gold_table": "gold.gold_revenue_by_nation"}
                    ],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "total_orders", "formula": "COUNT(DISTINCT o_orderkey)"},
                        {"table": "gold.gold_order_priority_summary", "kpi": "order_count", "formula": "COUNT(*)"},
                    ],
                    "severity": "CRITICAL_GOLD_JOIN",
                },
                "o_custkey": {
                    "role": "FOREIGN_KEY",
                    "silver": "silver_orders.o_custkey",
                    "gold_joins": [
                        {"target": "silver_customer.c_custkey", "gold_table": "gold.gold_revenue_by_nation"}
                    ],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "nation_attribution", "formula": "JOIN silver_customer.c_custkey"},
                    ],
                    "severity": "CRITICAL_GOLD_JOIN",
                },
                "o_orderstatus": {
                    "role": "DIMENSION_ATTRIBUTE",
                    "silver": "silver_orders.o_orderstatus",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_order_priority_summary", "kpi": "o_orderstatus", "formula": "GROUP BY o_orderstatus"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "o_totalprice": {
                    "role": "MEASURE",
                    "silver": "silver_orders.o_totalprice",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_order_priority_summary", "kpi": "total_value", "formula": "SUM(o_totalprice)"},
                        {"table": "gold.gold_order_priority_summary", "kpi": "avg_order_value", "formula": "AVG(o_totalprice)"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "o_orderdate": {
                    "role": "TIME_DIMENSION",
                    "silver": "silver_orders.o_orderdate",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "order_year", "formula": "EXTRACT(YEAR FROM o_orderdate)"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "o_orderpriority": {
                    "role": "DIMENSION_ATTRIBUTE",
                    "silver": "silver_orders.o_orderpriority",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_order_priority_summary", "kpi": "o_orderpriority", "formula": "GROUP BY o_orderpriority"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "o_clerk": {
                    "role": "AUDIT_ATTRIBUTE",
                    "silver": "silver_orders.o_clerk",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "o_shippriority": {
                    "role": "OPERATIONAL_ATTRIBUTE",
                    "silver": "silver_orders.o_shippriority",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "o_comment": {
                    "role": "FREE_TEXT_ATTRIBUTE",
                    "silver": "silver_orders.o_comment",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
            },
        },
        "lineitem": {
            "source": "source.lineitem",
            "bronze": "bronze.bronze_lineitem",
            "silver": "silver.silver_lineitem",
            "gold": [
                "gold.gold_revenue_by_nation",
            ],
            "columns": {
                "l_orderkey": {
                    "role": "FOREIGN_KEY",
                    "silver": "silver_lineitem.l_orderkey",
                    "gold_joins": [
                        {"target": "silver_orders.o_orderkey", "gold_table": "gold.gold_revenue_by_nation"}
                    ],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "order_item_linkage", "formula": "JOIN silver_orders.o_orderkey"}
                    ],
                    "severity": "CRITICAL_GOLD_JOIN",
                },
                "l_extendedprice": {
                    "role": "FINANCIAL_MEASURE",
                    "silver": "silver_lineitem.l_extendedprice",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "total_revenue", "formula": "SUM(l_extendedprice * (1 - l_discount))"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "l_discount": {
                    "role": "FINANCIAL_RATE",
                    "silver": "silver_lineitem.l_discount",
                    "gold_joins": [],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "total_revenue", "formula": "SUM(l_extendedprice * (1 - l_discount))"},
                        {"table": "gold.gold_revenue_by_nation", "kpi": "avg_discount", "formula": "AVG(l_discount)"},
                    ],
                    "severity": "HIGH_GOLD_KPI",
                },
                "l_quantity": {
                    "role": "OPERATIONAL_MEASURE",
                    "silver": "silver_lineitem.l_quantity",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "l_tax": {
                    "role": "FINANCIAL_RATE",
                    "silver": "silver_lineitem.l_tax",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "l_shipmode": {
                    "role": "LOGISTICS_ATTRIBUTE",
                    "silver": "silver_lineitem.l_shipmode",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "l_linenumber": {
                    "role": "LINE_IDENTIFIER",
                    "silver": "silver_lineitem.l_linenumber",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "l_suppkey": {
                    "role": "SUPPLIER_FOREIGN_KEY",
                    "silver": "silver_lineitem.l_suppkey",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
            },
        },
        "customer": {
            "source": "source.customer",
            "bronze": "bronze.bronze_customer",
            "silver": "silver.silver_customer",
            "gold": [
                "gold.gold_revenue_by_nation",
            ],
            "columns": {
                "c_custkey": {
                    "role": "PRIMARY_KEY",
                    "silver": "silver_customer.c_custkey",
                    "gold_joins": [
                        {"target": "silver_orders.o_custkey", "gold_table": "gold.gold_revenue_by_nation"}
                    ],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "customer_revenue_link", "formula": "JOIN silver_orders.o_custkey"}
                    ],
                    "severity": "CRITICAL_GOLD_JOIN",
                },
                "c_nationkey": {
                    "role": "FOREIGN_KEY",
                    "silver": "silver_customer.c_nationkey",
                    "gold_joins": [
                        {"target": "source.nation.n_nationkey", "gold_table": "gold.gold_revenue_by_nation"}
                    ],
                    "gold_kpis": [
                        {"table": "gold.gold_revenue_by_nation", "kpi": "nation", "formula": "JOIN source.nation.n_nationkey -> n_name"}
                    ],
                    "severity": "CRITICAL_GOLD_JOIN",
                },
                "c_name": {
                    "role": "ENTITY_NAME",
                    "silver": "silver_customer.c_name",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
                "c_acctbal": {
                    "role": "CUSTOMER_FINANCIAL_ATTRIBUTE",
                    "silver": "silver_customer.c_acctbal",
                    "gold_joins": [],
                    "gold_kpis": [],
                    "severity": "MEDIUM_SILVER_MART",
                },
            },
        },
    }
}


# ---------------------------------------------------------------------------
# Downstream Impact Tracer
# ---------------------------------------------------------------------------
def normalize_entity_name(entity_name: str) -> str:
    """Extract standard base table name from qualified reference."""
    clean = entity_name.lower().replace("source.", "").replace("bronze.", "").replace("silver.", "").replace("gold.", "")
    clean = clean.replace("bronze_", "").replace("silver_", "").replace("gold_", "")
    for base in ("orders", "lineitem", "customer"):
        if base in clean:
            return base
    return clean


def trace_downstream_impact(table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
    """Trace the downstream impact of schema or data failures on Silver and Gold layers.
    
    Returns:
        Dictionary containing affected silver models, gold tables, business KPIs,
        graph edges for visual rendering, and calculated blast scope severity.
    """
    base_name = normalize_entity_name(table_name)
    table_meta = LINEAGE_DAG["tables"].get(base_name)

    if not table_meta:
        return {
            "source_table": table_name,
            "base_table": base_name,
            "queried_columns": columns or [],
            "affected_silver_models": [],
            "affected_gold_tables": [],
            "affected_gold_kpis": [],
            "lineage_edges": [],
            "blast_scope_severity": "MEDIUM_SILVER_MART",
            "description": f"Entity {table_name} not registered in lakehouse lineage DAG."
        }

    all_cols = table_meta["columns"]
    target_cols = columns if columns else list(all_cols.keys())

    affected_silver = [table_meta["silver"]]
    affected_gold_set = set(table_meta["gold"])
    affected_kpis = []
    edges = [
        {"from": table_meta["source"], "to": table_meta["bronze"], "type": "INGESTION_ETL"},
        {"from": table_meta["bronze"], "to": table_meta["silver"], "type": "SILVER_CURATION"},
    ]
    for gt in table_meta["gold"]:
        edges.append({"from": table_meta["silver"], "to": gt, "type": "GOLD_AGGREGATION"})

    severities = []
    for col in target_cols:
        col_meta = all_cols.get(col)
        if not col_meta:
            severities.append("MEDIUM_SILVER_MART")
            continue
        severities.append(col_meta.get("severity", "MEDIUM_SILVER_MART"))
        for kpi in col_meta.get("gold_kpis", []):
            affected_kpis.append({
                "column": col,
                "table": kpi["table"],
                "kpi": kpi["kpi"],
                "formula": kpi["formula"]
            })
            edges.append({
                "from": f"{table_meta['silver']}.{col}",
                "to": f"{kpi['table']}.{kpi['kpi']}",
                "type": "COLUMN_TO_KPI"
            })

    if "CRITICAL_GOLD_JOIN" in severities:
        overall_severity = "CRITICAL_GOLD_JOIN"
    elif "HIGH_GOLD_KPI" in severities:
        overall_severity = "HIGH_GOLD_KPI"
    else:
        overall_severity = "MEDIUM_SILVER_MART"

    return {
        "source_table": table_meta["source"],
        "base_table": base_name,
        "queried_columns": target_cols,
        "affected_silver_models": affected_silver,
        "affected_gold_tables": sorted(list(affected_gold_set)),
        "affected_gold_kpis": affected_kpis,
        "lineage_edges": edges,
        "blast_scope_severity": overall_severity,
        "description": f"{len(target_cols)} column(s) in {base_name} affect {len(affected_silver)} Silver model(s) and {len(affected_gold_set)} Gold mart(s)."
    }


TYPE_GROUPS = {
    "BIGINT": {"BIGINT", "INTEGER", "INT8", "INT64", "HUGEINT"},
    "INTEGER": {"INTEGER", "INT", "INT4", "INT32", "SMALLINT", "TINYINT"},
    "DOUBLE": {"DOUBLE", "FLOAT8", "DECIMAL", "NUMERIC", "FLOAT", "REAL"},
    "VARCHAR": {"VARCHAR", "TEXT", "STRING", "CHAR", "BPCHAR"},
    "DATE": {"DATE"},
    "TIMESTAMP": {"TIMESTAMP", "DATETIME", "TIMESTAMPTZ"},
    "BOOLEAN": {"BOOLEAN", "BOOL"},
}


def are_types_compatible(expected: str, actual: str) -> bool:
    base_actual = actual.split("(")[0].strip().upper()
    exp = expected.split("(")[0].strip().upper()
    for group in TYPE_GROUPS.values():
        if exp in group and base_actual in group:
            return True
    return exp == base_actual


# ---------------------------------------------------------------------------
# Root-Cause Diff Analyzer
# ---------------------------------------------------------------------------
def compute_root_cause_diff(
    db_path: str,
    table_name: str,
    contract: dict[str, Any],
    violations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute exact diff between contract expectations and actual lakehouse table state.
    
    Categorizes the root cause into one of:
      - BREAKING_DDL_REMOVAL_OR_RENAME
      - UNREGISTERED_SCHEMA_EXTENSION
      - INCOMPATIBLE_TYPE_DRIFT
      - ROW_LEVEL_DATA_CORRUPTION
      - GLOBAL_DISTRIBUTION_DRIFT
    
    Recommends automated remediation:
      - PROMOTE_TO_ALLOWLIST_AND_RESUME
      - QUARANTINE_AND_REPAIR_ROWS
      - CIRCUIT_BREAKER_BLOCK_AND_ROLLBACK_GOLD
    """
    con = duckdb.connect(db_path, read_only=True)
    schema_name, tbl_name = parse_table_ref(table_name)

    # 1. Inspect actual schema
    actual_columns = {}
    try:
        info_rows = con.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_schema = '{schema_name}' AND table_name = '{tbl_name}'"
        ).fetchall()
        for r in info_rows:
            actual_columns[r[0].lower()] = str(r[1]).upper()
    except Exception:
        con.close()
        return {
            "table_name": table_name,
            "root_cause_category": "BREAKING_DDL_REMOVAL_OR_RENAME",
            "recommended_action": "CIRCUIT_BREAKER_BLOCK_AND_ROLLBACK_GOLD",
            "error": f"Table {table_name} does not exist in lakehouse engine."
        }

    expected_columns = {c["name"].lower(): str(c.get("type", "")).upper() for c in contract.get("columns", [])}
    allowed_extra = {c.lower() for c in contract.get("allowed_extra_columns", [])}

    missing_columns = [c for c in expected_columns if c not in actual_columns]
    unexpected_columns = [c for c in actual_columns if c not in expected_columns and c not in allowed_extra]
    type_mismatches = []
    for c, exp_t in expected_columns.items():
        if c in actual_columns:
            act_t = actual_columns[c]
            if not are_types_compatible(exp_t, act_t):
                type_mismatches.append({"column": c, "expected_type": exp_t, "actual_type": act_t})

    # 2. Inspect statistical metrics
    stats_diff = []
    total_rows = 0
    try:
        total_rows = con.execute(f"SELECT COUNT(*) FROM {schema_name}.{tbl_name}").fetchone()[0]
    except Exception:
        pass

    violated_cols = {v.get("column") for v in violations if v.get("column")}
    for v_col in (violated_cols or expected_columns.keys()):
        if v_col and v_col in actual_columns:
            col_info = next((c for c in contract.get("columns", []) if c["name"] == v_col), {})
            try:
                stat_row = con.execute(f"""
                    SELECT
                        COUNT(*) FILTER (WHERE {v_col} IS NULL) AS null_cnt,
                        MIN({v_col}) AS min_v,
                        MAX({v_col}) AS max_v,
                        AVG(TRY_CAST({v_col} AS DOUBLE)) AS avg_v
                    FROM {schema_name}.{tbl_name}
                """).fetchone()

                null_cnt = stat_row[0] or 0
                null_rate = round(null_cnt / total_rows, 5) if total_rows else 0.0
                min_v = stat_row[1]
                max_v = stat_row[2]
                avg_v = round(stat_row[3], 4) if stat_row[3] is not None else None

                stats_diff.append({
                    "column": v_col,
                    "row_count": total_rows,
                    "null_count": null_cnt,
                    "null_rate": null_rate,
                    "actual_min": min_v,
                    "actual_max": max_v,
                    "actual_mean": avg_v,
                    "contract_min": col_info.get("min_value"),
                    "contract_max": col_info.get("max_value"),
                    "contract_not_null": col_info.get("not_null", False),
                    "contract_allowed_values": col_info.get("allowed_values"),
                })
            except Exception:
                pass

    con.close()

    # 3. Categorize Root Cause & Determine Remediation
    violation_types = {v.get("type") for v in violations}
    if missing_columns or "MISSING_COLUMN" in violation_types:
        category = "BREAKING_DDL_REMOVAL_OR_RENAME"
        action = "CIRCUIT_BREAKER_BLOCK_AND_ROLLBACK_GOLD"
    elif type_mismatches or "TYPE_MISMATCH" in violation_types:
        category = "INCOMPATIBLE_TYPE_DRIFT"
        action = "CIRCUIT_BREAKER_BLOCK_AND_ROLLBACK_GOLD"
    elif unexpected_columns or "UNEXPECTED_COLUMN" in violation_types:
        category = "UNREGISTERED_SCHEMA_EXTENSION"
        action = "PROMOTE_TO_ALLOWLIST_AND_RESUME"
    elif "SEMANTIC_DRIFT" in violation_types:
        category = "GLOBAL_DISTRIBUTION_DRIFT"
        action = "CIRCUIT_BREAKER_BLOCK_AND_ROLLBACK_GOLD"
    else:
        category = "ROW_LEVEL_DATA_CORRUPTION"
        action = "QUARANTINE_AND_REPAIR_ROWS"

    return {
        "table_name": table_name,
        "total_rows": total_rows,
        "schema_diff": {
            "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
            "type_mismatches": type_mismatches,
            "expected_count": len(expected_columns),
            "actual_count": len(actual_columns),
        },
        "statistical_diff": stats_diff,
        "violations_count": len(violations),
        "violation_types": sorted(list(violation_types)),
        "root_cause_category": category,
        "recommended_action": action,
    }
