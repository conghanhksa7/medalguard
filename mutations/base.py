class BaseMutation:
    def __init__(self, sf=1.0):
        self.sf = sf
        self.applied = False

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def description(self):
        return "Base mutation"

    @property
    def category(self):
        return "BASE"
        
    @property
    def injected_fault_count(self):
        return 0

    @property
    def severity(self) -> str:
        return "BENIGN" if self.category == "BENIGN" else "HIGH"

    @property
    def schema_version(self) -> str:
        return "v1.0"

    @property
    def target_table(self) -> str:
        return "orders"

    @property
    def is_core(self) -> bool:
        return True

    def apply(self, con):
        raise NotImplementedError

    def revert(self, con):
        raise NotImplementedError
