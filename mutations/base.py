class BaseMutation:
    def __init__(self, sf=1.0):
        self.sf = sf
        self.applied = False

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return "Base mutation"

    @property
    def category(self) -> str:
        return "BASE"

    @property
    def severity(self) -> str:
        """One of: CRITICAL, HIGH, MEDIUM, BENIGN."""
        if self.category == "BENIGN":
            return "BENIGN"
        if self.category == "DESTRUCTIVE":
            return "CRITICAL"
        return "HIGH"

    @property
    def schema_version(self) -> str:
        """Semantic schema evolution version tag (e.g., v1.0, v1.1-additive, v2.0-breaking)."""
        if self.category == "ADDITIVE":
            return "v1.1-unregistered"
        if self.category in ("DESTRUCTIVE", "TYPE_CHANGE"):
            return "v2.0-breaking"
        if self.category == "BENIGN":
            return "v1.1-compatible"
        return "v1.0-data"

    @property
    def target_table(self) -> str:
        """Primary target source table: lineitem, orders, or customer."""
        return "lineitem"

    @property
    def is_core(self) -> bool:
        """True if part of the original 19-scenario Milestone 2/3 core benchmark."""
        return True

    @property
    def injected_fault_count(self) -> int:
        return 0

    def to_metadata(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "severity": self.severity,
            "schema_version": self.schema_version,
            "target_table": self.target_table,
            "is_core": self.is_core,
            "injected_fault_count": self.injected_fault_count,
            "description": self.description,
        }

    def apply(self, con):
        raise NotImplementedError

    def revert(self, con):
        raise NotImplementedError
