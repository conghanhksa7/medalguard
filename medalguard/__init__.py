"""MedalGuard: Contract-Aware Early Data Failure Detection Framework for Medallion Lakehouses."""

__version__ = "2.0.0"

from medalguard.config import (
    load_contract,
    load_all_contracts,
    validate_contract_schema,
)
from medalguard.gate import (
    ContractGate,
    ContractViolationError,
    ValidationResult,
    MeasurementType,
)
from medalguard.lineage import (
    LINEAGE_DAG,
    trace_downstream_impact,
    compute_root_cause_diff,
)
from medalguard.replay import (
    ReplayAndRecoveryEngine,
)
from medalguard.alerting import (
    AlertDispatcher,
    evaluate_alert_metrics,
)

__all__ = [
    "__version__",
    "load_contract",
    "load_all_contracts",
    "validate_contract_schema",
    "ContractGate",
    "ContractViolationError",
    "ValidationResult",
    "MeasurementType",
    "LINEAGE_DAG",
    "trace_downstream_impact",
    "compute_root_cause_diff",
    "ReplayAndRecoveryEngine",
    "AlertDispatcher",
    "evaluate_alert_metrics",
]
