"""M2: Destructive mutations — Drop or rename existing columns."""
from mutations.base import BaseMutation


class M2a_DropNonKey(BaseMutation):
    """Drop a non-key column (l_tax) from lineitem."""

    @property
    def description(self):
        return "Drop l_tax column from lineitem (breaking change)"

    @property
    def category(self):
        return "DESTRUCTIVE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-breaking"

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
        con.execute("ALTER TABLE source.lineitem DROP COLUMN l_tax")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M2b_DropKeyCol(BaseMutation):
    """Drop a primary key column (l_orderkey) from lineitem."""

    @property
    def description(self):
        return "Drop l_orderkey (PK) from lineitem — catastrophic"

    @property
    def category(self):
        return "DESTRUCTIVE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-breaking"

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
        con.execute("ALTER TABLE source.lineitem DROP COLUMN l_orderkey")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.lineitem")
            con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M2c_RenameCol(BaseMutation):
    """Rename l_discount to l_rebate — column exists but with wrong name."""

    @property
    def description(self):
        return "Rename l_discount -> l_rebate in lineitem"

    @property
    def category(self):
        return "DESTRUCTIVE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-breaking"

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
        con.execute("ALTER TABLE source.lineitem RENAME COLUMN l_discount TO l_rebate")
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.lineitem RENAME COLUMN l_rebate TO l_discount")
            except Exception:
                con.execute("DROP TABLE IF EXISTS source.lineitem")
                con.execute("ALTER TABLE source._lineitem_backup RENAME TO lineitem")
            self.applied = False


class M2d_DropCustomerNationKey(BaseMutation):
    """Drop foreign key column c_nationkey from customer (breaking join)."""

    @property
    def description(self):
        return "Drop foreign key column c_nationkey from customer (breaking join)"

    @property
    def category(self):
        return "DESTRUCTIVE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-breaking"

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
        con.execute("ALTER TABLE source.customer DROP COLUMN c_nationkey")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("DROP TABLE IF EXISTS source.customer")
            con.execute("ALTER TABLE source._customer_backup RENAME TO customer")
            self.applied = False


class M2e_RenameOrdersPriority(BaseMutation):
    """Rename o_orderpriority -> o_priority_tier in orders."""

    @property
    def description(self):
        return "Rename o_orderpriority -> o_priority_tier in orders"

    @property
    def category(self):
        return "DESTRUCTIVE"

    @property
    def severity(self) -> str:
        return "CRITICAL"

    @property
    def schema_version(self) -> str:
        return "v2.0-breaking"

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
        con.execute("ALTER TABLE source.orders RENAME COLUMN o_orderpriority TO o_priority_tier")
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.orders RENAME COLUMN o_priority_tier TO o_orderpriority")
            except Exception:
                con.execute("DROP TABLE IF EXISTS source.orders")
                con.execute("ALTER TABLE source._orders_backup RENAME TO orders")
            self.applied = False
