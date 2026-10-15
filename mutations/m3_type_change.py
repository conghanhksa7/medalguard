"""M3: Type change mutations — Change column data types."""
from mutations.base import BaseMutation


class M3a_DoubleToVarchar(BaseMutation):
    """Change l_quantity from DOUBLE to VARCHAR (incompatible)."""

    @property
    def description(self):
        return "Cast l_quantity DOUBLE -> VARCHAR in lineitem"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("""
            CREATE OR REPLACE TABLE source.lineitem AS
            SELECT
                * EXCLUDE (l_quantity),
                CAST(l_quantity AS VARCHAR) AS l_quantity
            FROM source._lineitem_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M3b_IntegerToDouble(BaseMutation):
    """Widen l_linenumber from INTEGER to DOUBLE (may be benign)."""

    @property
    def description(self):
        return "Cast l_linenumber INTEGER -> DOUBLE (widening, possibly benign)"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._lineitem_backup AS SELECT * FROM source.lineitem")
        con.execute("""
            CREATE OR REPLACE TABLE source.lineitem AS
            SELECT
                * EXCLUDE (l_linenumber),
                CAST(l_linenumber AS DOUBLE) AS l_linenumber
            FROM source._lineitem_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M3c_DateToVarchar(BaseMutation):
    """Change o_orderdate from DATE to VARCHAR in orders."""

    @property
    def description(self):
        return "Cast o_orderdate DATE -> VARCHAR in orders"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def injected_fault_count(self):
        return int(1_500_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
        con.execute("""
            CREATE OR REPLACE TABLE source.orders AS
            SELECT
                * EXCLUDE (o_orderdate),
                CAST(o_orderdate AS VARCHAR) AS o_orderdate
            FROM source._orders_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False
