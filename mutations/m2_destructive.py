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
    def injected_fault_count(self):
        # All rows affected when column is dropped
        return int(6_000_000 * self.sf)  # ~6M rows at SF=1

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
