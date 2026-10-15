"""M1: Additive mutations — Add new columns to source tables."""
from mutations.base import BaseMutation


class M1a_AddSingleCol(BaseMutation):
    """Add a single new column to lineitem."""

    @property
    def description(self):
        return "Add l_promo_code VARCHAR(20) to lineitem"

    @property
    def category(self):
        return "ADDITIVE"

    @property
    def injected_fault_count(self):
        return 0  # Additive is not inherently faulty

    def apply(self, con):
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_promo_code VARCHAR(20) DEFAULT 'NONE'
        """)
        con.execute("""
            UPDATE source.lineitem
            SET l_promo_code = CASE
                WHEN l_linenumber % 10 = 0 THEN 'PROMO10'
                WHEN l_linenumber % 5 = 0 THEN 'SALE5'
                ELSE 'NONE'
            END
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            try:
                con.execute("ALTER TABLE source.lineitem DROP COLUMN l_promo_code")
            except Exception:
                pass
            self.applied = False


class M1b_AddMultiCol(BaseMutation):
    """Add 3 new columns simultaneously to lineitem."""

    @property
    def description(self):
        return "Add 3 columns (l_promo_code, l_warehouse_id, l_batch_ts) to lineitem"

    @property
    def category(self):
        return "ADDITIVE"

    @property
    def injected_fault_count(self):
        return 0

    def apply(self, con):
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_promo_code VARCHAR(20) DEFAULT 'NONE'
        """)
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_warehouse_id INTEGER DEFAULT 1
        """)
        con.execute("""
            ALTER TABLE source.lineitem
            ADD COLUMN l_batch_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            for col in ['l_promo_code', 'l_warehouse_id', 'l_batch_ts']:
                try:
                    con.execute(f"ALTER TABLE source.lineitem DROP COLUMN {col}")
                except Exception:
                    pass
            self.applied = False
