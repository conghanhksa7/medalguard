"""M5: Semantic drift mutations — Value shifts that preserve schema but violate domain semantics."""
from mutations.base import BaseMutation


class M5a_MULTIPLY_100(BaseMutation):
    """Multiply l_extendedprice by 100 — extreme drift."""

    @property
    def description(self):
        return "Multiply l_extendedprice by 100 (extreme semantic drift)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v1.0-semantic"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("UPDATE source.lineitem SET l_extendedprice = l_extendedprice * 100")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M5b_MULTIPLY_1_5(BaseMutation):
    """Multiply l_extendedprice by 1.5 — moderate drift."""

    @property
    def description(self):
        return "Multiply l_extendedprice by 1.5 (moderate semantic drift)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-semantic"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("UPDATE source.lineitem SET l_extendedprice = l_extendedprice * 1.5")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M5c_CATEGORICAL_SHIFT(BaseMutation):
    """Insert 10 rows with unlisted status 'X'."""

    @property
    def description(self):
        return "Insert 10 rows with invalid orderstatus 'X'"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0-semantic"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    @property
    def injected_fault_count(self):
        return 10

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
        max_key = con.execute("SELECT MAX(o_orderkey) FROM source.orders").fetchone()[0]
        con.execute(f"""
            INSERT INTO source.orders
            SELECT
                o_orderkey + {max_key + 1},
                o_custkey, 'X', o_totalprice, o_orderdate,
                o_orderpriority, o_clerk, o_shippriority, o_comment
            FROM source.orders
            LIMIT 10
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False


class M5d_LineitemTaxSpike(BaseMutation):
    """Multiply l_tax * 10 in lineitem (tax rate unit error: 0.04 -> 0.40)."""

    @property
    def description(self):
        return "Multiply l_tax * 10 in lineitem (tax rate unit error: 0.04 -> 0.40)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v1.0-stat-drift"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("UPDATE source.lineitem SET l_tax = l_tax * 10")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M5e_ShipmodeInvalidCode(BaseMutation):
    """Change lineitem l_shipmode values to unlisted code 'DRONE'."""

    @property
    def description(self):
        return f"Change {max(1, int(150 * self.sf))} lineitem l_shipmode values to unlisted code 'DRONE'"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def severity(self) -> str:
        return "MEDIUM"

    @property
    def schema_version(self) -> str:
        return "v1.0-domain-drift"

    @property
    def target_table(self) -> str:
        return "lineitem"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return max(1, int(150 * self.sf))

    def apply(self, con):
        n = self.injected_fault_count
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE _bad_shipkeys AS
            SELECT l_orderkey, l_linenumber
            FROM source.lineitem
            ORDER BY l_orderkey, l_linenumber
            LIMIT {n}
        """)
        con.execute("""
            UPDATE source.lineitem
            SET l_shipmode = 'DRONE'
            WHERE (l_orderkey, l_linenumber) IN (
                SELECT l_orderkey, l_linenumber FROM _bad_shipkeys
            )
        """)
        con.execute("DROP TABLE IF EXISTS _bad_shipkeys")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False
