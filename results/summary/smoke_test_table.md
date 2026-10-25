| Config | Mutation | Pipeline Status | Detected | DDI | Detection Stage | Quarantined Rows | QE (%) | Blast Radius | Wall-clock (ms) | dbt (ms) | Validation (ms) |
|:---|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **C1** | `M2a_DropNonKey` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 22,118 | 3,912 | 0 |
| **C1** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 14,720 | 1,085 | 0 |
| **C1** | `M5a_MULTIPLY_100` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **92.1%** | 22,169 | 2,737 | 0 |
| **C1** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 23,508 | 3,336 | 0 |
| **C2** | `M2a_DropNonKey` | `CRASH` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 17,280 | 930 | 0 |
| **C2** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 15,640 | 2,103 | 47 |
| **C2** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 29,058 | 2,700 | 60 |
| **C2** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 25,177 | 2,960 | 56 |
| **C3_standalone** | `M2a_DropNonKey` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 9,745 | 1,464 | 182 |
| **C3_standalone** | `M4a_NullAndNegative` | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 30 | 100% | **0.0%** | 38,314 | 4,339 | 1,186 |
| **C3_standalone** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 17,517 | 3,268 | 456 |
| **C3_standalone** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 114,070 | 15,014 | 2,322 |
| **C3** | `M2a_DropNonKey` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 51,859 | 6,622 | 580 |
| **C3** | `M4a_NullAndNegative` | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 30 | 100% | **0.0%** | 157,941 | 17,901 | 3,755 |
| **C3** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 56,513 | 6,572 | 877 |
| **C3** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 153,772 | 19,157 | 2,875 |
