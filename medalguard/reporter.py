"""Violation reporting and blast radius calculation."""
import json
import re
from datetime import datetime
from pathlib import Path


class ViolationReporter:
    """Logs violations and calculates blast radius."""

    def calculate_blast_radius(self, injected_fault_count: int,
                               db_path: str, table: str, violations: list[dict] = None) -> float:
        """Estimate source fault leakage ratio at gate level: |uncontained faulty records| / |injected records|.

        NOTE: This is gate-level source fault leakage estimation (0.0 = fully contained, 1.0 = fully leaked).
        The actual Gold layer Blast Radius (BR_gold_impact) is measured end-to-end by diff_gold()
        comparing final Gold tables against clean baseline reference.

        Returns 0.0 if no violations or injected_fault_count is 0,
        otherwise ratio of affected rows to injected count.
        """
        if not violations or injected_fault_count == 0:
            return 0.0
        
        # Sum up affected rows from constraint violations
        affected = sum(
            v.get("affected_rows", 0) for v in violations
            if "affected_rows" in v
        )
        
        if affected == 0:
            # Schema-level violations (missing column, type mismatch) affect all injected records
            schema_violations = [v for v in violations if v["type"] in {
                "MISSING_COLUMN", "TYPE_MISMATCH", "UNEXPECTED_COLUMN",
                "TABLE_NOT_FOUND", "SEMANTIC_DRIFT"
            }]
            if schema_violations:
                return 1.0  # 100% blast radius
            return 0.0
            
        return min(affected / injected_fault_count, 1.0)

    def save_report(self, gate_name: str, violations: list[dict],
                    blast_radius: float, output_dir: str = "results/raw/gate_reports",
                    experiment_id: str = ""):
        """Save violation report to JSON file."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_gate_name = re.sub(r'[^\w\-_\.]', '_', gate_name)
        if experiment_id:
            safe_exp_id = re.sub(r'[^\w\-_\.]', '_', experiment_id)
            filename = f"{safe_exp_id}_{safe_gate_name}_{timestamp}.json"
        else:
            filename = f"{safe_gate_name}_{timestamp}.json"
        
        report = {
            "gate": gate_name,
            "experiment_id": experiment_id,
            "timestamp": timestamp,
            "total_violations": len(violations),
            "blast_radius": round(blast_radius, 6),
            "violations": violations
        }
        
        filepath = Path(output_dir) / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        
        return str(filepath)
