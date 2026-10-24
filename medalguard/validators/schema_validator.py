"""Schema drift detection: compare actual table schema against contract."""
import duckdb


class SchemaValidator:
    """Detects missing columns, unexpected columns, and type mismatches."""

    # Map of compatible type groups
    TYPE_GROUPS = {
        "BIGINT": {"BIGINT", "INTEGER", "INT8", "INT64", "HUGEINT"},
        "INTEGER": {"INTEGER", "INT", "INT4", "INT32", "SMALLINT", "TINYINT"},
        "DOUBLE": {"DOUBLE", "FLOAT8", "DECIMAL", "NUMERIC", "FLOAT", "REAL"},
        "VARCHAR": {"VARCHAR", "TEXT", "STRING", "CHAR", "BPCHAR"},
        "DATE": {"DATE"},
        "TIMESTAMP": {"TIMESTAMP", "DATETIME", "TIMESTAMPTZ"},
        "BOOLEAN": {"BOOLEAN", "BOOL"},
    }

    def check(self, con: duckdb.DuckDBPyConnection, source_table: str,
              target_table: str, contract: dict) -> list[dict]:
        """Check schema of target_table against contract definition.
        
        Returns list of violation dicts.
        """
        violations = []

        from ..utils import parse_table_ref, quote_table, quote_identifier
        
        # Get actual columns from target table
        schema_name, table_name = parse_table_ref(target_table)
        
        actual_cols = {}
        try:
            rows = con.execute(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                f"WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'"
            ).fetchall()
            actual_cols = {row[0].lower(): row[1].upper() for row in rows}
        except Exception as e:
            violations.append({
                "type": "TABLE_NOT_FOUND",
                "table": target_table,
                "message": f"Cannot read schema for '{target_table}': {e}"
            })
            return violations

        if not actual_cols:
            return [{
                "type": "TABLE_NOT_FOUND",
                "table": target_table,
                "message": f"Table '{target_table}' not found"
            }]

        # Check each column in contract
        contract_col_names = set()
        for col_spec in contract["columns"]:
            col_name = col_spec["name"].lower()
            contract_col_names.add(col_name)
            expected_type = col_spec["type"].upper()

            if col_name not in actual_cols:
                violations.append({
                    "type": "MISSING_COLUMN",
                    "column": col_name,
                    "message": f"Column '{col_name}' defined in contract but missing in table"
                })
            elif not self._types_compatible(actual_cols[col_name], expected_type):
                violations.append({
                    "type": "TYPE_MISMATCH",
                    "column": col_name,
                    "expected": expected_type,
                    "actual": actual_cols[col_name],
                    "message": f"Column '{col_name}': expected {expected_type}, got {actual_cols[col_name]}"
                })

        # Check for unexpected columns (schema drift)
        strict_columns = contract.get("strict_columns", True)
        allowed_extra = {c.lower() for c in contract.get("allowed_extra_columns", [])}
        for actual_col in actual_cols:
            if actual_col not in contract_col_names and actual_col not in allowed_extra:
                if strict_columns:
                    violations.append({
                        "type": "UNEXPECTED_COLUMN",
                        "column": actual_col,
                        "message": f"Column '{actual_col}' found in table but not in contract (schema drift)"
                    })

        return violations

    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if actual DB type is compatible with expected contract type."""
        import re
        actual_upper = re.sub(r'\(.*?\)', '', actual.upper()).strip()
        expected_upper = re.sub(r'\(.*?\)', '', expected.upper()).strip()
        
        if actual_upper == expected_upper:
            return True
        
        for canonical, aliases in self.TYPE_GROUPS.items():
            if expected_upper in aliases or expected_upper == canonical:
                return actual_upper in aliases or actual_upper == canonical
        
        return False
