"""Constraint validation: NOT NULL, value ranges, allowed values, UNIQUE."""
import duckdb
from ..utils import quote_identifier, quote_table, parse_table_ref

NUMERIC_TEMPORAL = (
    "INT", "BIGINT", "INTEGER", "SMALLINT", "TINYINT", "HUGEINT",
    "DOUBLE", "DECIMAL", "NUMERIC", "FLOAT", "REAL",
    "DATE", "TIMESTAMP", "TIME"
)


class ConstraintValidator:
    """Validates data constraints defined in contract."""

    def check(self, con: duckdb.DuckDBPyConnection, table: str,
              contract: dict) -> list[dict]:
        """Check constraint violations on table data.
        
        Returns list of violation dicts with affected_rows count.
        """
        violations = []
        q_table = quote_table(table)
        schema_name, table_name = parse_table_ref(table)

        try:
            rows = con.execute(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                f"WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'"
            ).fetchall()
            actual_cols = {row[0].lower(): row[1].upper() for row in rows}
        except Exception as e:
            actual_cols = {}

        if not actual_cols:
            return []

        for col_spec in contract.get("columns", []):
            col_name = col_spec["name"]
            if col_name.lower() not in actual_cols:
                continue  # Missing column handled by SchemaValidator

            q_col = quote_identifier(col_name)
            actual_type = actual_cols[col_name.lower()]

            # Check NOT NULL
            if col_spec.get("not_null", False):
                try:
                    null_count = con.execute(
                        f"SELECT COUNT(*) FROM {q_table} WHERE {q_col} IS NULL"
                    ).fetchone()[0]
                    if null_count > 0:
                        violations.append({
                            "type": "NULL_VIOLATION",
                            "column": col_name,
                            "affected_rows": null_count,
                            "message": f"Column '{col_name}' has {null_count} NULL values (contract requires NOT NULL)"
                        })
                except Exception as e:
                    raise RuntimeError(f"Constraint query failed on {table}.{col_name}: {e}") from e

            # Check unique
            if col_spec.get("unique", False):
                try:
                    dup_count = con.execute(
                        f"SELECT COUNT(*) - COUNT(DISTINCT {q_col}) "
                        f"FROM {q_table} WHERE {q_col} IS NOT NULL"
                    ).fetchone()[0]
                    if dup_count > 0:
                        violations.append({
                            "type": "UNIQUE_VIOLATION",
                            "column": col_name,
                            "affected_rows": int(dup_count),
                            "message": f"Column '{col_name}' has {dup_count} duplicate key rows (contract requires UNIQUE)"
                        })
                except Exception as e:
                    raise RuntimeError(f"Constraint query failed on {table}.{col_name}: {e}") from e

            # Check min_value
            if "min_value" in col_spec:
                if any(t in actual_type for t in NUMERIC_TEMPORAL):
                    try:
                        below_count = con.execute(
                            f"SELECT COUNT(*) FROM {q_table} WHERE {q_col} < {col_spec['min_value']}"
                        ).fetchone()[0]
                        if below_count > 0:
                            violations.append({
                                "type": "RANGE_VIOLATION",
                                "column": col_name,
                                "constraint": f">= {col_spec['min_value']}",
                                "affected_rows": below_count,
                                "message": f"Column '{col_name}' has {below_count} values below minimum {col_spec['min_value']}"
                            })
                    except Exception as e:
                        raise RuntimeError(f"Constraint query failed on {table}.{col_name}: {e}") from e

            # Check max_value
            if "max_value" in col_spec:
                if any(t in actual_type for t in NUMERIC_TEMPORAL):
                    try:
                        above_count = con.execute(
                            f"SELECT COUNT(*) FROM {q_table} WHERE {q_col} > {col_spec['max_value']}"
                        ).fetchone()[0]
                        if above_count > 0:
                            violations.append({
                                "type": "RANGE_VIOLATION",
                                "column": col_name,
                                "constraint": f"<= {col_spec['max_value']}",
                                "affected_rows": above_count,
                                "message": f"Column '{col_name}' has {above_count} values above maximum {col_spec['max_value']}"
                            })
                    except Exception as e:
                        raise RuntimeError(f"Constraint query failed on {table}.{col_name}: {e}") from e

            # Check allowed_values
            if "allowed_values" in col_spec:
                allowed = col_spec["allowed_values"]
                values_str = ", ".join(f"'{v}'" for v in allowed)
                try:
                    invalid_count = con.execute(
                        f"SELECT COUNT(*) FROM {q_table} "
                        f"WHERE {q_col} IS NOT NULL AND {q_col} NOT IN ({values_str})"
                    ).fetchone()[0]
                    if invalid_count > 0:
                        violations.append({
                            "type": "ALLOWED_VALUES_VIOLATION",
                            "column": col_name,
                            "allowed": allowed,
                            "affected_rows": invalid_count,
                            "message": f"Column '{col_name}' has {invalid_count} values not in {allowed}"
                        })
                except Exception as e:
                    raise RuntimeError(f"Constraint query failed on {table}.{col_name}: {e}") from e

        return violations
