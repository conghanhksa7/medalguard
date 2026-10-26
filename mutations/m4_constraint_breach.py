"""M4: Constraint breach mutations — Inject value-level violations."""
from mutations.base import BaseMutation


class M4a_NullAndNegative(BaseMutation):
    """Inject 100 NULL o_custkey + 200 negative o_totalprice in orders."""

    @property
    def description(self):
        return (f"Inject {int(100 * self.sf)} NULL custkey + "
                f"{int(200 * self.sf)} negative totalprice")

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-row-fault"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return int(300 * self.sf)

    def apply(self, con):
        n_null = int(100 * self.sf)
        n_neg = int(200 * self.sf)

        # DuckDB dbgen creates tables with NOT NULL constraints by default
        con.execute("ALTER TABLE source.orders ALTER o_custkey DROP NOT NULL")
        con.execute("ALTER TABLE source.orders ALTER o_totalprice DROP NOT NULL")

        con.execute(f"""
            UPDATE source.orders
            SET o_custkey = NULL
            WHERE o_orderkey IN (
                SELECT o_orderkey FROM source.orders ORDER BY o_orderkey LIMIT {n_null}
            )
        """)
        con.execute(f"""
            UPDATE source.orders
            SET o_totalprice = -1 * ABS(o_totalprice)
            WHERE o_orderkey IN (
                SELECT o_orderkey FROM source.orders
                WHERE o_custkey IS NOT NULL
                ORDER BY o_orderkey
                LIMIT {n_neg}
            )
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class M4b_NullSmall(BaseMutation):
    """Inject only 5 NULL rows — subtle, tests sensitivity."""

    @property
    def description(self):
        return "Inject only 5 NULL o_custkey (subtle)"

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def severity(self) -> str:
        return "MEDIUM"

    @property
    def schema_version(self) -> str:
        return "v1.0-row-fault"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 5  # Fixed small count regardless of SF

    def apply(self, con):
        con.execute("ALTER TABLE source.orders ALTER o_custkey DROP NOT NULL")
        con.execute("""
            UPDATE source.orders
            SET o_custkey = NULL
            WHERE o_orderkey IN (
                SELECT o_orderkey FROM source.orders ORDER BY o_orderkey LIMIT 5
            )
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False


class M4c_DuplicateKeys(BaseMutation):
    """Insert 5 duplicate o_orderkey rows into source.orders."""

    @property
    def description(self):
        return "Inject 5 duplicate o_orderkey rows"

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-row-fault"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 5

    def apply(self, con):
        con.execute("""
            CREATE TABLE IF NOT EXISTS source._orders_backup AS
            SELECT * FROM source.orders
        """)
        # Duplicate the first 5 rows
        con.execute("""
            INSERT INTO source.orders
            SELECT * FROM source.orders
            ORDER BY o_orderkey
            LIMIT 5
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class M4d_LineitemNegativeQty(BaseMutation):
    """Inject negative l_quantity (-5.0) rows into lineitem."""

    @property
    def description(self):
        return f"Inject {max(1, int(250 * self.sf))} negative l_quantity (-5.0) rows into lineitem"

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-row-fault"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return max(1, int(250 * self.sf))

    def apply(self, con):
        n = self.injected_fault_count
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE _bad_keys AS
            SELECT l_orderkey, l_linenumber
            FROM source.lineitem
            ORDER BY l_orderkey, l_linenumber
            LIMIT {n}
        """)
        con.execute("""
            UPDATE source.lineitem
            SET l_quantity = -5.0
            WHERE (l_orderkey, l_linenumber) IN (
                SELECT l_orderkey, l_linenumber FROM _bad_keys
            )
        """)
        con.execute("DROP TABLE IF EXISTS _bad_keys")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M4e_CustomerDuplicateKeys(BaseMutation):
    """Insert duplicate c_custkey rows into customer."""

    @property
    def description(self):
        return f"Insert {max(1, int(100 * self.sf))} duplicate c_custkey rows into customer"

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-row-fault"

    @property
    def target_table(self) -> str:
        return "customer"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return max(1, int(100 * self.sf))

    def apply(self, con):
        n = self.injected_fault_count
        con.execute("CREATE TABLE IF NOT EXISTS source._customer_backup AS SELECT * FROM source.customer")
        con.execute(f"""
            INSERT INTO source.customer
            SELECT * FROM source.customer
            ORDER BY c_custkey
            LIMIT {n}
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.customer")
            con.execute("ALTER TABLE source._customer_backup RENAME TO customer")
            self.applied = False
