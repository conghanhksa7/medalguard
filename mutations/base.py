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

    def apply(self, con):
        raise NotImplementedError

    def revert(self, con):
        raise NotImplementedError
