# MedalGuard Mutation Suite v2 Catalog (36 Scenarios)

**Tổng số:** 36 kịch bản (24 Harmful Faults + 12 Benign Schema Evolution).

## 1. Bảng Danh Mục Toàn Bộ 36 Kịch Bản

| STT | Tên Kịch Bản | Nhóm Suite | Danh Mục | Bảng Đích | Mức Độ (Severity) | Phiên Bản Schema | Số Bản Ghi Lỗi |
|:---:|:---|:---:|:---|:---:|:---:|:---:|:---:|
| 1 | `M1a_AddSingleCol` | **Core** | `ADDITIVE` | `lineitem` | `MEDIUM` | `v1.1-unregistered` | 0 |
| 2 | `M1b_AddMultiCol` | **Core** | `ADDITIVE` | `lineitem` | `MEDIUM` | `v1.2-unregistered` | 0 |
| 3 | `M1c_AddCustomerPiiCol` | **Expanded** | `ADDITIVE` | `customer` | `HIGH` | `v1.1-unregistered-pii` | 0 |
| 4 | `M1d_AddOrdersShadowCol` | **Expanded** | `ADDITIVE` | `orders` | `MEDIUM` | `v1.1-unregistered` | 0 |
| 5 | `M2a_DropNonKey` | **Core** | `DESTRUCTIVE` | `lineitem` | `CRITICAL` | `v2.0-breaking` | 600,000 |
| 6 | `M2b_DropKeyCol` | **Core** | `DESTRUCTIVE` | `lineitem` | `CRITICAL` | `v2.0-breaking` | 600,000 |
| 7 | `M2c_RenameCol` | **Core** | `DESTRUCTIVE` | `lineitem` | `CRITICAL` | `v2.0-breaking` | 600,000 |
| 8 | `M2d_DropCustomerNationKey` | **Expanded** | `DESTRUCTIVE` | `customer` | `CRITICAL` | `v2.0-breaking` | 15,000 |
| 9 | `M2e_RenameOrdersPriority` | **Expanded** | `DESTRUCTIVE` | `orders` | `CRITICAL` | `v2.0-breaking` | 150,000 |
| 10 | `M3a_DoubleToVarchar` | **Core** | `TYPE_CHANGE` | `lineitem` | `HIGH` | `v2.0-type-drift` | 600,000 |
| 11 | `M3b_IntegerToDouble` | **Core** | `TYPE_CHANGE` | `lineitem` | `MEDIUM` | `v2.0-type-drift` | 600,000 |
| 12 | `M3c_DateToVarchar` | **Core** | `TYPE_CHANGE` | `orders` | `HIGH` | `v2.0-type-drift` | 150,000 |
| 13 | `M3d_CustomerAcctbalToVarchar` | **Expanded** | `TYPE_CHANGE` | `customer` | `HIGH` | `v2.0-type-drift` | 15,000 |
| 14 | `M3e_OrdersCustkeyToVarchar` | **Expanded** | `TYPE_CHANGE` | `orders` | `CRITICAL` | `v2.0-type-drift` | 150,000 |
| 15 | `M4a_NullAndNegative` | **Core** | `CONSTRAINT_BREACH` | `orders` | `HIGH` | `v1.0-constraint` | 30 |
| 16 | `M4b_NullSmall` | **Core** | `CONSTRAINT_BREACH` | `orders` | `MEDIUM` | `v1.0-constraint` | 5 |
| 17 | `M4c_DuplicateKeys` | **Core** | `CONSTRAINT_BREACH` | `orders` | `HIGH` | `v1.0-constraint` | 5 |
| 18 | `M4d_LineitemNegativeQty` | **Expanded** | `CONSTRAINT_BREACH` | `lineitem` | `HIGH` | `v1.0-constraint` | 25 |
| 19 | `M4e_CustomerDuplicateKeys` | **Expanded** | `CONSTRAINT_BREACH` | `customer` | `HIGH` | `v1.0-constraint` | 10 |
| 20 | `M5a_MULTIPLY_100` | **Core** | `SEMANTIC_DRIFT` | `lineitem` | `CRITICAL` | `v1.0-semantic` | 600,000 |
| 21 | `M5b_MULTIPLY_1_5` | **Core** | `SEMANTIC_DRIFT` | `lineitem` | `HIGH` | `v1.0-semantic` | 600,000 |
| 22 | `M5c_CATEGORICAL_SHIFT` | **Core** | `SEMANTIC_DRIFT` | `orders` | `HIGH` | `v1.0-semantic` | 10 |
| 23 | `M5d_LineitemTaxSpike` | **Expanded** | `SEMANTIC_DRIFT` | `lineitem` | `CRITICAL` | `v1.0-semantic` | 600,000 |
| 24 | `M5e_ShipmodeInvalidCode` | **Expanded** | `SEMANTIC_DRIFT` | `lineitem` | `MEDIUM` | `v1.0-semantic` | 15 |
| 25 | `B1_AddColumn` | **Core** | `BENIGN` | `lineitem` | `BENIGN` | `v1.1-compatible` | 0 |
| 26 | `B2_ValueInRange` | **Core** | `BENIGN` | `lineitem` | `BENIGN` | `v1.1-compatible` | 0 |
| 27 | `B3_InsertRows` | **Core** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 28 | `B4_ReorderCols` | **Expanded** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 29 | `B5_AddValidStatus` | **Core** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 30 | `B6_IncreasePrecision` | **Expanded** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 31 | `B7_LargeBatchInsert` | **Core** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 32 | `B8_WhitespaceValues` | **Expanded** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 33 | `B9_AddOrdersAuditCol` | **Expanded** | `BENIGN` | `orders` | `BENIGN` | `v1.1-compatible` | 0 |
| 34 | `B10_AddCustomerAuditCol` | **Expanded** | `BENIGN` | `customer` | `BENIGN` | `v1.1-compatible` | 0 |
| 35 | `B11_LineitemQuantityInRange` | **Expanded** | `BENIGN` | `lineitem` | `BENIGN` | `v1.1-compatible` | 0 |
| 36 | `B12_CustomerAcctbalUpdate` | **Expanded** | `BENIGN` | `customer` | `BENIGN` | `v1.1-compatible` | 0 |

## 2. Kết Quả Kiểm Chứng Gate 1 Trên 17 Kịch Bản Mở Rộng Mới

| Kịch Bản | Loại | Trạng Thái Gate 1 | Phát Hiện | DDI | Tầng Phát Hiện | Số Dòng Cách Ly | Vi Phạm | Kết Quả |
|:---|:---:|:---:|:---:|:---:|:---|:---:|:---:|:---:|
| `M1c_AddCustomerPiiCol` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M1d_AddOrdersShadowCol` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M2d_DropCustomerNationKey` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M2e_RenameOrdersPriority` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 2 | **PASS** |
| `M3d_CustomerAcctbalToVarchar` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M3e_OrdersCustkeyToVarchar` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M4d_LineitemNegativeQty` | Harmful | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 25 | 1 | **PASS** |
| `M4e_CustomerDuplicateKeys` | Harmful | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 10 | 1 | **PASS** |
| `M5d_LineitemTaxSpike` | Harmful | `BLOCKED` | **True** | 0 | `PRE_TRANSFORM` | 0 | 1 | **PASS** |
| `M5e_ShipmodeInvalidCode` | Harmful | `SUCCESS` | **True** | 0 | `PRE_TRANSFORM` | 15 | 1 | **PASS** |
| `B4_ReorderCols` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B6_IncreasePrecision` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B8_WhitespaceValues` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B9_AddOrdersAuditCol` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B10_AddCustomerAuditCol` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B11_LineitemQuantityInRange` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
| `B12_CustomerAcctbalUpdate` | Benign | `SUCCESS` | **False** | -1 | `NOT_DETECTED` | 0 | 0 | **PASS** |
