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
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v2.0-type-drift"

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
    """Cast l_linenumber BIGINT -> DOUBLE in lineitem (widening, possibly benign)."""

    @property
    def description(self):
        return "Cast l_linenumber BIGINT -> DOUBLE in lineitem (widening, possibly benign)"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def severity(self) -> str:
        return "MEDIUM"

    @property
    def schema_version(self) -> str:
        return "v2.0-type-drift"

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
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v2.0-type-drift"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

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


class M3d_CustomerAcctbalToVarchar(BaseMutation):
    """Cast c_acctbal DOUBLE -> VARCHAR in customer."""

    @property
    def description(self):
        return "Cast c_acctbal DOUBLE -> VARCHAR in customer"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def severity(self) -> str:
        return "HIGH"

    @property
    def schema_version(self) -> str:
        return "v2.0-type-drift"

    @property
    def target_table(self) -> str:
        return "customer"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return int(150_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._customer_backup AS SELECT * FROM source.customer")
        con.execute("""
            CREATE OR REPLACE TABLE source.customer AS
            SELECT
                * EXCLUDE (c_acctbal),
                CAST(c_acctbal AS VARCHAR) AS c_acctbal
            FROM source._customer_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.customer")
            con.execute("ALTER TABLE source._customer_backup RENAME TO customer")
            self.applied = False


class M3e_OrdersCustkeyToVarchar(BaseMutation):
    """Cast foreign key o_custkey BIGINT -> VARCHAR in orders."""

    @property
    def description(self):
        return "Cast foreign key o_custkey BIGINT -> VARCHAR in orders"

    @property
    def category(self):
        return "TYPE_CHANGE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-type-drift"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return False

    @property
    def injected_fault_count(self):
        return int(1_500_000 * self.sf)

    def apply(self, con):
        con.execute("CREATE TABLE IF NOT EXISTS source._orders_backup AS SELECT * FROM source.orders")
        con.execute("""
            CREATE OR REPLACE TABLE source.orders AS
            SELECT
                * EXCLUDE (o_custkey),
                CAST(o_custkey AS VARCHAR) AS o_custkey
            FROM source._orders_backup
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.orders")
            con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False
