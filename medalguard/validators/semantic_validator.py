"""Semantic drift detection: statistical distribution anomalies."""
import duckdb


class SemanticValidator:
    """Detects semantic drift by comparing column statistics against expected ranges."""

    def check(self, con: duckdb.DuckDBPyConnection, source_table: str,
              target_table: str, contract: dict) -> list[dict]:
        """Check for semantic drift using quality_rules in contract.
        
        Supports rules: mean_range, null_rate, row_count.
        """
        from ..utils import quote_identifier, quote_table
        violations = []

        for rule in contract.get("quality_rules", []):
            rule_type = rule["rule"]

            if rule_type == "mean_range":
                violations += self._check_mean_range(
                    con, target_table, rule["column"],
                    rule["min"], rule["max"]
                )
            elif rule_type == "null_rate":
                violations += self._check_null_rate(
                    con, target_table, rule["column"], rule["max"]
                )
            elif rule_type == "row_count":
                violations += self._check_row_count(
                    con, target_table, rule.get("min", 1)
                )

        return violations

    def _check_mean_range(self, con, table, column, expected_min, expected_max) -> list:
        """Check if column mean falls within expected range."""
        from ..utils import quote_identifier, quote_table
        q_table = quote_table(table)
        q_col = quote_identifier(column)
        try:
            result = con.execute(
                f"SELECT AVG({q_col}) FROM {q_table} WHERE {q_col} IS NOT NULL"
            ).fetchone()
            actual_mean = result[0] if result else None
            
            if actual_mean is not None and (actual_mean < expected_min or actual_mean > expected_max):
                return [{
                    "type": "SEMANTIC_DRIFT",
                    "column": column,
                    "expected_range": f"[{expected_min}, {expected_max}]",
                    "actual_mean": round(actual_mean, 6),
                    "message": f"Column '{column}' mean = {actual_mean:.6f}, expected in [{expected_min}, {expected_max}] (semantic drift detected)"
                }]
        except Exception:
            pass
        return []

    def _check_null_rate(self, con, table, column, max_rate) -> list:
        """Check if null rate exceeds maximum allowed."""
        from ..utils import quote_identifier, quote_table
        q_table = quote_table(table)
        q_col = quote_identifier(column)
        try:
            result = con.execute(
                f"SELECT COUNT(*) FILTER (WHERE {q_col} IS NULL)::DOUBLE / COUNT(*)::DOUBLE "
                f"FROM {q_table}"
            ).fetchone()
            actual_rate = result[0] if result else 0
            
            if actual_rate > max_rate:
                return [{
                    "type": "NULL_RATE_EXCEEDED",
                    "column": column,
                    "max_allowed": max_rate,
                    "actual_rate": round(actual_rate, 6),
                    "message": f"Column '{column}' null rate = {actual_rate:.4%}, exceeds max {max_rate:.4%}"
                }]
        except Exception:
            pass
        return []

    def _check_row_count(self, con, table, min_rows) -> list:
        """Check if table has minimum number of rows."""
        from ..utils import quote_table
        q_table = quote_table(table)
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {q_table}").fetchone()[0]
            if count < min_rows:
                return [{
                    "type": "ROW_COUNT_LOW",
                    "table": table,
                    "min_expected": min_rows,
                    "actual_count": count,
                    "message": f"Table '{table}' has {count} rows, expected at least {min_rows}"
                }]
        except Exception:
            pass
        return []
