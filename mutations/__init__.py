"""MedalGuard Mutation Suite v2 (Core 19 scenarios + Expanded 36 scenarios)."""
from .m1_additive import (
    M1a_AddSingleCol, M1b_AddMultiCol, M1c_AddCustomerPiiCol, M1d_AddOrdersShadowCol
)
from .m2_destructive import (
    M2a_DropNonKey, M2b_DropKeyCol, M2c_RenameCol, M2d_DropCustomerNationKey, M2e_RenameOrdersPriority
)
from .m3_type_change import (
    M3a_DoubleToVarchar, M3b_IntegerToDouble, M3c_DateToVarchar, M3d_CustomerAcctbalToVarchar, M3e_OrdersCustkeyToVarchar
)
from .m4_constraint_breach import (
    M4a_NullAndNegative, M4b_NullSmall, M4c_DuplicateKeys, M4d_LineitemNegativeQty, M4e_CustomerDuplicateKeys
)
from .m5_semantic_drift import (
    M5a_MULTIPLY_100, M5b_MULTIPLY_1_5, M5c_CATEGORICAL_SHIFT, M5d_LineitemTaxSpike, M5e_ShipmodeInvalidCode
)
from .benign_mutations import (
    B1_AddColumn, B2_ValueInRange, B3_InsertRows, B4_ReorderCols,
    B5_AddValidStatus, B6_IncreasePrecision, B7_LargeBatchInsert, B8_WhitespaceValues,
    B9_AddOrdersAuditCol, B10_AddCustomerAuditCol, B11_LineitemQuantityInRange, B12_CustomerAcctbalUpdate
)


def get_mutation_suite(sf: float = 0.1, suite: str = "core") -> tuple[list, list]:
    """Return (fault_mutations, benign_mutations).
    
    suite='core': 14 harmful + 5 benign = 19 scenarios.
    suite='expanded': 24 harmful + 12 benign = 36 scenarios.
    """
    core_faults = [
        M1a_AddSingleCol(sf), M1b_AddMultiCol(sf),
        M2a_DropNonKey(sf), M2b_DropKeyCol(sf), M2c_RenameCol(sf),
        M3a_DoubleToVarchar(sf), M3b_IntegerToDouble(sf), M3c_DateToVarchar(sf),
        M4a_NullAndNegative(sf), M4b_NullSmall(sf), M4c_DuplicateKeys(sf),
        M5a_MULTIPLY_100(sf), M5b_MULTIPLY_1_5(sf), M5c_CATEGORICAL_SHIFT(sf),
    ]
    core_benigns = [
        B1_AddColumn(sf), B2_ValueInRange(sf), B3_InsertRows(sf),
        B5_AddValidStatus(sf), B7_LargeBatchInsert(sf),
    ]

    if suite == "core":
        return core_faults, core_benigns

    expanded_faults = [
        # M1 (4)
        M1a_AddSingleCol(sf), M1b_AddMultiCol(sf), M1c_AddCustomerPiiCol(sf), M1d_AddOrdersShadowCol(sf),
        # M2 (5)
        M2a_DropNonKey(sf), M2b_DropKeyCol(sf), M2c_RenameCol(sf), M2d_DropCustomerNationKey(sf), M2e_RenameOrdersPriority(sf),
        # M3 (5)
        M3a_DoubleToVarchar(sf), M3b_IntegerToDouble(sf), M3c_DateToVarchar(sf), M3d_CustomerAcctbalToVarchar(sf), M3e_OrdersCustkeyToVarchar(sf),
        # M4 (5)
        M4a_NullAndNegative(sf), M4b_NullSmall(sf), M4c_DuplicateKeys(sf), M4d_LineitemNegativeQty(sf), M4e_CustomerDuplicateKeys(sf),
        # M5 (5)
        M5a_MULTIPLY_100(sf), M5b_MULTIPLY_1_5(sf), M5c_CATEGORICAL_SHIFT(sf), M5d_LineitemTaxSpike(sf), M5e_ShipmodeInvalidCode(sf),
    ]
    expanded_benigns = [
        B1_AddColumn(sf), B2_ValueInRange(sf), B3_InsertRows(sf), B4_ReorderCols(sf),
        B5_AddValidStatus(sf), B6_IncreasePrecision(sf), B7_LargeBatchInsert(sf), B8_WhitespaceValues(sf),
        B9_AddOrdersAuditCol(sf), B10_AddCustomerAuditCol(sf), B11_LineitemQuantityInRange(sf), B12_CustomerAcctbalUpdate(sf),
    ]

    return expanded_faults, expanded_benigns
