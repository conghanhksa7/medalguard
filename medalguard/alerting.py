"""MedalGuard Multi-Channel Alerting & Incident Notification Engine.

Provides:
1. Webhook JSON payload dispatching (Slack/PagerDuty schema).
2. Professional HTML/Text email notifications with lineage and root-cause evidence.
3. Alert precision, recall, MTTD, and MTTR evaluation metrics.
"""
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALERTS_DIR = PROJECT_ROOT / "results" / "alerts"


class AlertDispatcher:
    """Dispatches lakehouse contract incidents to Webhook and Email channels."""

    def __init__(self, output_dir: Path | str = ALERTS_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def dispatch_incident(
        self,
        incident_id: str,
        gate_name: str,
        mutation_name: str,
        severity: str,
        mttd_ms: float,
        root_cause_diff: dict[str, Any],
        downstream_lineage: dict[str, Any],
        auto_remediation: dict[str, Any],
        pipeline_status: str = "BLOCKED",
    ) -> dict[str, Any]:
        """Generate and dispatch both Webhook JSON payload and HTML email alert."""
        timestamp = datetime.now().isoformat()
        clean_id = re.sub(r'[^\w\-_\.]', '_', incident_id)

        # 1. Build Webhook Payload (Slack / PagerDuty schema)
        webhook_payload = {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "severity": severity,
            "status": "RESOLVED" if auto_remediation.get("status") in ("APPROVED_AND_RESUMED", "REPAIRED_AND_REPLAYED") else "TRIGGERED",
            "gate_name": gate_name,
            "mutation_name": mutation_name,
            "pipeline_status": pipeline_status,
            "mttd_ms": mttd_ms,
            "channel": "#lakehouse-data-observability",
            "pagerduty": {
                "service": "Medalhouse-Bronze-Gate",
                "urgency": "high" if severity in ("CRITICAL", "HIGH") else "medium",
                "client": "MedalGuard-Core-Engine"
            },
            "root_cause_diff": root_cause_diff,
            "downstream_lineage": {
                "affected_silver": downstream_lineage.get("affected_silver_models", []),
                "affected_gold": downstream_lineage.get("affected_gold_tables", []),
                "affected_kpis": [k["kpi"] for k in downstream_lineage.get("affected_gold_kpis", [])],
                "blast_scope_severity": downstream_lineage.get("blast_scope_severity", "HIGH_GOLD_KPI"),
            },
            "auto_remediation": auto_remediation
        }

        webhook_path = self.output_dir / f"webhook_{clean_id}.json"
        with open(webhook_path, "w", encoding="utf-8") as f:
            json.dump(webhook_payload, f, indent=2, default=str)

        # 2. Build Rich HTML Email
        kpi_list_html = "".join(
            f"<li><b>{k['kpi']}</b> ({k['table']}) &rarr; <code>{k['formula']}</code></li>"
            for k in downstream_lineage.get("affected_gold_kpis", [])[:6]
        ) or "<li>None (Operational Mart Boundary Isolated)</li>"

        action_badge_color = "#28a745" if "RESUME" in str(auto_remediation.get("status")) or "REPAIR" in str(auto_remediation.get("status")) else "#dc3545"
        severity_color = "#d9534f" if severity == "CRITICAL" else "#f0ad4e" if severity == "HIGH" else "#0275d8"

        email_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>MedalGuard Alert: {incident_id}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f4f6f8; color: #222; }}
    .card {{ background: #fff; max-width: 720px; margin: 0 auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; }}
    .header {{ background: #1a202c; color: #fff; padding: 20px 24px; border-bottom: 4px solid {severity_color}; }}
    .header h2 {{ margin: 0; font-size: 20px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; background: {severity_color}; color: #fff; }}
    .content {{ padding: 24px; }}
    table.meta {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    table.meta td {{ padding: 8px 12px; border: 1px solid #e2e8f0; font-size: 13px; }}
    table.meta td.label {{ background: #f8fafc; font-weight: 600; width: 32%; }}
    .section-title {{ font-size: 14px; font-weight: 700; text-transform: uppercase; color: #4a5568; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #edf2f7; padding-bottom: 4px; }}
    .remediation-box {{ background: #f0fff4; border: 1px solid #c6f6d5; border-radius: 6px; padding: 14px; margin-top: 15px; }}
    .footer {{ background: #f8fafc; padding: 12px 24px; font-size: 11px; color: #718096; text-align: center; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2>
        <span>MedalGuard Incident Alert</span>
        <span class="badge">{severity}</span>
      </h2>
    </div>
    <div class="content">
      <table class="meta">
        <tr><td class="label">Incident ID</td><td><code>{incident_id}</code></td></tr>
        <tr><td class="label">Timestamp</td><td>{timestamp}</td></tr>
        <tr><td class="label">Boundary Gate</td><td><b>{gate_name}</b></td></tr>
        <tr><td class="label">Fault / Mutation</td><td><code>{mutation_name}</code></td></tr>
        <tr><td class="label">Mean Time to Detect (MTTD)</td><td><b>{mttd_ms:,.1f} ms</b></td></tr>
        <tr><td class="label">Root Cause Category</td><td><b>{root_cause_diff.get('root_cause_category', 'UNKNOWN')}</b></td></tr>
        <tr><td class="label">Recommended Action</td><td><code>{root_cause_diff.get('recommended_action', 'CIRCUIT_BREAKER')}</code></td></tr>
      </table>

      <div class="section-title">Downstream Lineage & KPI Exposure</div>
      <p style="font-size: 13px; color: #4a5568;">
        The fault was intercepted at <b>{gate_name}</b> before corrupting:
      </p>
      <ul style="font-size: 13px; color: #2d3748; line-height: 1.6;">
        {kpi_list_html}
      </ul>

      <div class="remediation-box">
        <h4 style="margin: 0 0 6px 0; color: #22543d; font-size: 13px;">Automated Remediation Engine</h4>
        <div style="font-size: 12px; color: #276749;">
          Status: <b style="color: {action_badge_color};">{auto_remediation.get('status', 'EXECUTED')}</b> |
          Availability: <b>{auto_remediation.get('availability_pct', 100.0):.1f}%</b> |
          Post-Remediation Blast Radius: <b>{auto_remediation.get('blast_radius', auto_remediation.get('post_replay_blast_radius', 0.0)):.1%}</b>
        </div>
      </div>
    </div>
    <div class="footer">
      Generated automatically by MedalGuard Observability Platform &bull; Medallion Lakehouse Early Failure Guard
    </div>
  </div>
</body>
</html>
"""
        email_path = self.output_dir / f"email_{clean_id}.html"
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(email_html)

        return {
            "incident_id": incident_id,
            "webhook_path": str(webhook_path),
            "email_path": str(email_path),
            "severity": severity,
            "mttd_ms": mttd_ms,
        }


def evaluate_alert_metrics(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate Alert Precision, Coverage (Recall), Mean MTTD, and Mean MTTR.
    
    Harmful mutations detected -> True Positive (TP)
    Benign mutations falsely alerted -> False Positive (FP)
    Harmful mutations missed -> False Negative (FN)
    """
    tp = sum(1 for inc in incidents if not inc.get("is_benign", False) and inc.get("alerted", False))
    fp = sum(1 for inc in incidents if inc.get("is_benign", False) and inc.get("alerted", False))
    fn = sum(1 for inc in incidents if not inc.get("is_benign", False) and not inc.get("alerted", False))

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0

    mttd_vals = [inc["mttd_ms"] for inc in incidents if "mttd_ms" in inc and inc["mttd_ms"] is not None]
    mttr_vals = [inc["mttr_ms"] for inc in incidents if "mttr_ms" in inc and inc["mttr_ms"] is not None]

    mean_mttd = round(sum(mttd_vals) / len(mttd_vals), 2) if mttd_vals else 0.0
    mean_mttr = round(sum(mttr_vals) / len(mttr_vals), 2) if mttr_vals else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "alert_precision": precision,
        "alert_precision_pct": round(precision * 100, 2),
        "alert_recall_coverage": recall,
        "alert_recall_coverage_pct": round(recall * 100, 2),
        "mean_mttd_ms": mean_mttd,
        "mean_mttr_ms": mean_mttr,
    }
