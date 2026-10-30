| Config | Mutation | Pipeline Status | Detected | DDI | Detection Stage | Quarantined Rows | QE (%) | Blast Radius | Wall-clock (ms) | dbt (ms) | Validation (ms) |
|:---|:---|:---:|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **C1** | `M2a_DropNonKey` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 18,101 | 1,022 | 0 |
| **C1** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 1 | `SILVER_CONTRACT` | 0 | N/A | **0.0%** | 17,472 | 1,103 | 0 |
| **C1** | `M5a_MULTIPLY_100` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **92.1%** | 23,009 | 2,539 | 0 |
| **C1** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 23,583 | 2,832 | 0 |
| **C2** | `M2a_DropNonKey` | `CRASH` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 16,005 | 999 | 0 |
| **C2** | `M4a_NullAndNegative` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 15,602 | 2,048 | 75 |
| **C2** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 2 | `POST_TRANSFORM` | 0 | N/A | **0.0%** | 15,809 | 2,162 | 74 |
| **C2** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 23,134 | 2,529 | 89 |
| **C3_standalone** | `M2a_DropNonKey` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 8,130 | 944 | 174 |
| **C3_standalone** | `M4a_NullAndNegative` | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 30 | 100% | **0.0%** | 24,186 | 2,548 | 739 |
| **C3_standalone** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 8,239 | 1,056 | 191 |
| **C3_standalone** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 23,922 | 2,658 | 359 |
| **C3** | `M2a_DropNonKey` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 8,884 | 1,020 | 175 |
| **C3** | `M4a_NullAndNegative` | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 30 | 100% | **0.0%** | 24,299 | 2,736 | 799 |
| **C3** | `M5a_MULTIPLY_100` | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | N/A | **0.0%** | 8,096 | 960 | 182 |
| **C3** | `B1_AddColumn` | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | N/A | **0.0%** | 23,998 | 2,760 | 455 |
