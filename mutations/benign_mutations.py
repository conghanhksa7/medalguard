"""Benign mutations — Legitimate changes that should NOT trigger violations.

Used to measure False Positive Rate (FPR).
All benign mutations have injected_fault_count = 0.
"""
from mutations.base import BaseMutation


class B1_AddColumn(BaseMutation):
    """Add a legitimate comment column (additive, valid with strict_columns=false or allowed_extra)."""

    @property
    def description(self):
        return "Add l_internal_note VARCHAR to lineitem (benign additive)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-compatible"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return True

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
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-compatible"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("""
            UPDATE source.lineitem
            SET l_discount = 0.08
            WHERE l_linenumber = 1
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
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
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-compatible"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
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
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B4_ReorderCols(BaseMutation):
    """Reorder columns physically in orders table."""

    @property
    def description(self):
        return "Recreate orders table with columns in different order"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-reorder"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return False

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
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-compatible"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
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
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B6_IncreasePrecision(BaseMutation):
    """Widen o_totalprice precision to DECIMAL(18,4) in orders."""

    @property
    def description(self):
        return "Widen o_totalprice precision (benign type widening)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-widening"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
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
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-compatible"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
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
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B8_WhitespaceValues(BaseMutation):
    """Add trailing spaces to o_comment in 50 rows of orders."""

    @property
    def description(self):
        return "Add trailing spaces to o_comment (still valid values)"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.0-benign-data"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
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
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class B9_AddOrdersAuditCol(BaseMutation):
    """Add allowed extra column o_internal_note to orders."""

    @property
    def description(self):
        return "Add allowed extra column o_internal_note VARCHAR to orders"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-allowlisted"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("ALTER TABLE source.orders ADD COLUMN o_internal_note VARCHAR DEFAULT 'audit-ok'")
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.orders DROP COLUMN o_internal_note")
            except Exception:
                pass
            self.applied = False


class B10_AddCustomerAuditCol(BaseMutation):
    """Add allowed extra column c_internal_note to customer."""

    @property
    def description(self):
        return "Add allowed extra column c_internal_note VARCHAR to customer"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.1-allowlisted"

    @property
    def target_table(self) -> str:
        return "customer"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("ALTER TABLE source.customer ADD COLUMN c_internal_note VARCHAR DEFAULT 'kyc-verified'")
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.customer DROP COLUMN c_internal_note")
            except Exception:
                pass
            self.applied = False


class B11_QuantityInRange(BaseMutation):
    """Adjust l_quantity = 26.0 on first 50 rows of lineitem (valid range [1, 50])."""

    @property
    def description(self):
        return "Update l_quantity = 26.0 for 50 rows in lineitem (valid range [1, 50])"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.0-benign-data"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("""
            CREATE OR REPLACE TEMP TABLE _b11_keys AS
            SELECT l_orderkey, l_linenumber FROM source.lineitem
            ORDER BY l_orderkey, l_linenumber LIMIT 50
        """)
        con.execute("""
            UPDATE source.lineitem
            SET l_quantity = 26.0
            WHERE (l_orderkey, l_linenumber) IN (SELECT l_orderkey, l_linenumber FROM _b11_keys)
        """)
        con.execute("DROP TABLE IF EXISTS _b11_keys")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class B12_CustomerBalUpdate(BaseMutation):
    """Update c_acctbal = 2500.00 for first 50 rows in customer (valid range [-1000, 10000])."""

    @property
    def description(self):
        return "Update c_acctbal = 2500.00 for 50 rows in customer (valid range [-1000, 10000])"

    @property
    def category(self):
        return "BENIGN"

    @property
    def severity(self) -> str:
        return "BENIGN"

    @property
    def schema_version(self) -> str:
        return "v1.0-benign-data"

    @property
    def target_table(self) -> str:
        return "customer"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._customer_backup AS SELECT * FROM source.customer")
        con.execute("""
            CREATE OR REPLACE TEMP TABLE _b12_keys AS
            SELECT c_custkey FROM source.customer
            ORDER BY c_custkey LIMIT 50
        """)
        con.execute("""
            UPDATE source.customer
            SET c_acctbal = 2500.00
            WHERE c_custkey IN (SELECT c_custkey FROM _b12_keys)
        """)
        con.execute("DROP TABLE IF EXISTS _b12_keys")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.customer")
            con.execute("ALTER TABLE source._customer_backup RENAME TO customer")
            self.applied = False


# Aliases for backward compatibility
B11_LineitemQuantityInRange = B11_QuantityInRange
B12_CustomerAcctbalUpdate = B12_CustomerBalUpdate
