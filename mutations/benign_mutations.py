"""Benign mutations — Legitimate changes that should NOT trigger violations.

Used to measure False Positive Rate (FPR).
All benign mutations have injected_fault_count = 0.
"""
from mutations.base import BaseMutation


class B1_AddColumn(BaseMutation):
    """Add a legitimate comment column (additive, valid with strict_columns=false)."""

    @property
    def description(self):
        return "Add l_internal_note VARCHAR to lineitem (benign additive)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_internal_note VARCHAR DEFAULT 'auto-generated'
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.lineitem DROP COLUMN l_internal_note")
            except Exception:
                pass
            self.applied = False


class B2_ValueInRange(BaseMutation):
    """Change discount values within allowed range (0.05 -> 0.08)."""

    @property
    def description(self):
        return "Shift l_discount within range (still 0.0-0.10)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        # Set some discounts to 0.08 (within [0.0, 0.10])
        con.execute("""
            UPDATE source.lineitem
            SET l_discount = 0.08
            WHERE l_linenumber = 1
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class B3_InsertRows(BaseMutation):
    """Insert new legitimate orders with valid values."""

    @property
    def description(self):
        return "Insert 100 valid new orders"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        max_key = con.execute("SELECT MAX(o_orderkey) FROM source.orders").fetchone()[0]
        n = int(100 * self.sf)
        con.execute(f"""
            INSERT INTO source.orders
            SELECT
                o_orderkey + {max_key + 1},
                o_custkey,
                o_orderstatus,
                o_totalprice,
                o_orderdate,
                o_orderpriority,
                o_clerk,
                o_shippriority,
                o_comment
            FROM source.orders
            ORDER BY o_orderkey
            LIMIT {n}
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class B4_ReorderCols(BaseMutation):
    """Reorder columns in source — should not affect output."""

    @property
    def description(self):
        return "Recreate orders table with columns in different order"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
        con.execute("""
            CREATE OR REPLACE TABLE source.orders AS
            SELECT
                o_comment, o_clerk, o_orderstatus, o_orderkey,
                o_custkey, o_totalprice, o_orderdate,
                o_orderpriority, o_shippriority
            FROM source._orders_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B5_AddValidStatus(BaseMutation):
    """Insert rows with existing valid orderstatus values."""

    @property
    def description(self):
        return "Insert orders with valid status 'O', 'F', 'P'"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        max_key = con.execute("SELECT MAX(o_orderkey) FROM source.orders").fetchone()[0]
        con.execute(f"""
            INSERT INTO source.orders
            SELECT
                o_orderkey + {max_key + 1},
                o_custkey, 'O', o_totalprice, o_orderdate,
                o_orderpriority, o_clerk, o_shippriority, o_comment
            FROM source.orders
            WHERE o_orderstatus = 'F'
            LIMIT 30
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class B6_IncreasePrecision(BaseMutation):
    """Change DECIMAL precision (widening — should be compatible)."""

    @property
    def description(self):
        return "Widen o_totalprice precision (benign type widening)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        # DuckDB handles precision widening gracefully
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
        con.execute("""
            CREATE OR REPLACE TABLE source.orders AS
            SELECT
                * EXCLUDE (o_totalprice),
                CAST(o_totalprice AS DECIMAL(18,4)) AS o_totalprice
            FROM source._orders_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B7_LargeBatchInsert(BaseMutation):
    """Insert 2x current row count — tests mean_range sensitivity."""

    @property
    def description(self):
        return "Double orders table size with valid copies"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        max_key = con.execute("SELECT MAX(o_orderkey) FROM source.orders").fetchone()[0]
        con.execute(f"""
            INSERT INTO source.orders
            SELECT
                o_orderkey + {max_key + 1},
                o_custkey, o_orderstatus, o_totalprice, o_orderdate,
                o_orderpriority, o_clerk, o_shippriority, o_comment
            FROM source.orders
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class B8_WhitespaceValues(BaseMutation):
    """Add trailing spaces to VARCHAR columns — edge case test."""

    @property
    def description(self):
        return "Add trailing spaces to o_orderstatus (still valid values)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        # Note: This MAY trigger allowed_values check if trimming is not done
        # That would be a legitimate false positive to report
        con.execute("""
            UPDATE source.orders
            SET o_comment = o_comment || '   '
            WHERE o_orderkey IN (
                SELECT o_orderkey FROM source.orders LIMIT 50
            )
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False
