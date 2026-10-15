"""M5: Semantic drift mutations — Schema unchanged, values wrong."""
from mutations.base import BaseMutation


class M5a_MULTIPLY_100(BaseMutation):
    """Multiply l_discount by 100: 0.05 -> 5.0 (obvious drift)."""

    @property
    def description(self):
        return "Multiply l_discount * 100 (0.05 -> 5.0)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("UPDATE source.lineitem SET l_discount = l_discount * 100")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("UPDATE source.lineitem SET l_discount = l_discount / 100")
            self.applied = False


class M5b_MULTIPLY_1_5(BaseMutation):
    """Multiply l_discount by 1.5: subtle drift, mean ~0.05 -> ~0.075."""

    @property
    def description(self):
        return "Multiply l_discount * 1.5 (subtle, mean 0.05 -> 0.075)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def injected_fault_count(self):
        return int(6_000_000 * self.sf)

    def apply(self, con):
        con.execute("UPDATE source.lineitem SET l_discount = l_discount * 1.5")
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("UPDATE source.lineitem SET l_discount = l_discount / 1.5")
            self.applied = False


class M5c_CATEGORICAL_SHIFT(BaseMutation):
    """Add new orderstatus 'X' not in allowed values [O, F, P]."""

    @property
    def description(self):
        return f"Change {int(100 * self.sf)} orders o_orderstatus to 'X' (not in allowed set)"

    @property
    def category(self):
        return "SEMANTIC_DRIFT"

    @property
    def injected_fault_count(self):
        return int(100 * self.sf)

    def apply(self, con):
        n = int(100 * self.sf)
        con.execute(f"""
            UPDATE source.orders
            SET o_orderstatus = 'X'
            WHERE o_orderkey IN (
                SELECT o_orderkey FROM source.orders ORDER BY o_orderkey LIMIT {n}
            )
        """)
        self.applied = True

    def revert(self, con):
        if self.applied:
            con.execute("LOAD tpch;")
            con.execute(f"CALL dbgen(sf={self.sf}, schema='source', overwrite=true)")
            self.applied = False
