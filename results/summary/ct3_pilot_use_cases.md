# MedalGuard CT3 Pilot Task-Based Verification Report

**Scale Factor:** 0.1 | **Total Pilot Incidents:** 3 | **Alert Precision:** 100.0% | **Gold Availability:** 100.0%

## 1. Executive Pilot Scorecard

| Pilot Use Case | Gate Intercept | MTTD (ms) | MTTR (ms) | Pre-Replay BR | Post-Replay BR | Data Loss | Gold Availability | Remediation Method |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Legitimate Schema Evolution & Dynamic Allowlist Approval** | `B->S:lineitem` | **101.1** | **7,777.6** | 0.00% | **0.0%** | **0.0%** | **100.0%** | Promoted l_promo_code to allowlist, updated contract v1 -> v2, resumed pipeline. |
| **Row-level Data Corruption, Isolation, Automated Repair & Backfill** | `B->S:orders` | **540.1** | **8,345.5** | 21.58% | **0.0%** | **0.0%** | **100.0%** | Deduplicated 5 duplicate keys, repaired & backfilled 30 rows from clean LKG reference, replayed Silver & Gold. |
| **Catastrophic Semantic Drift, Circuit Breaker & Sub-Second LKG Rollback** | `B->S:lineitem` | **115.8** | **51.9** | 0.00% | **0.0%** | **0.0%** | **100.0%** | Activated Circuit Breaker, intercepted at Gate 1, performed sub-second LKG Gold rollback in 51.9 ms. |

## 2. SLA Metrics Summary

- **Mean Time to Detect (MTTD):** 252.30 ms

- **Mean Time to Recover (MTTR):** 5391.67 ms

- **Alert Precision:** 100.0% (Zero false alarms on benign schema evolution)

- **Alert Recall / Coverage:** 100.0%

- **Post-Replay Data Loss Rate:** 0.0%

- **Post-Replay Gold Availability:** 100.0%

