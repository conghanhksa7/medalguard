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
    def injected_fault_count(self):
        return 5  # Fixed small count regardless of SF

    def apply(self, con):
        # DuckDB dbgen creates tables with NOT NULL constraints by default
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
    """Insert rows with duplicate o_orderkey values."""

    @property
    def description(self):
        return f"Insert {int(50 * self.sf)} rows with duplicate o_orderkey (PK violation)"

    @property
    def category(self):
        return "CONSTRAINT_BREACH"

    @property
    def injected_fault_count(self):
        return int(50 * self.sf)

    def apply(self, con):
        n_dupes = int(50 * self.sf)
        # Copy first N rows and re-insert (creates duplicates)
        con.execute(f"""
            INSERT INTO source.orders
            SELECT * FROM source.orders
            ORDER BY o_orderkey
            LIMIT {n_dupes}
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False
