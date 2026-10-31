"""Load and parse MedalGuard YAML contract definitions."""
import yaml
from pathlib import Path

VALID_DATA_TYPES = {
    "BIGINT", "INTEGER", "DOUBLE", "DECIMAL", "NUMERIC",
    "FLOAT", "REAL", "VARCHAR", "TEXT", "STRING",
    "DATE", "TIMESTAMP", "BOOLEAN"
}

VALID_QUALITY_RULES = {"row_count", "null_rate", "mean_range"}


def validate_contract_schema(contract: dict, contract_path: str = "<memory>") -> bool:
    """Validate that a parsed contract conforms to the MedalGuard specification.
    
    Args:
        contract: Parsed YAML contract dictionary.
        contract_path: Path or identifier for logging/error reporting.
        
    Returns:
        True if valid.
        
    Raises:
        ValueError: If any validation rule is violated.
    """
    if not isinstance(contract, dict):
        raise ValueError(f"Contract must be a dictionary, got {type(contract)} in {contract_path}")

    # 1. Required keys
    required_keys = ["table", "source_table", "columns"]
    for key in required_keys:
        if key not in contract:
            raise ValueError(f"Contract missing required field: '{key}' in {contract_path}")

    # 2. Columns list validation
    columns = contract.get("columns")
    if not isinstance(columns, list) or len(columns) == 0:
        raise ValueError(f"'columns' must be a non-empty list in {contract_path}")

    for idx, col in enumerate(columns):
        if not isinstance(col, dict):
            raise ValueError(f"Column #{idx} must be a dictionary in {contract_path}")
        
        col_name = col.get("name")
        if not col_name or not isinstance(col_name, str):
            raise ValueError(f"Column #{idx} missing valid 'name' in {contract_path}")
        
        col_type = col.get("type")
        if not col_type or not isinstance(col_type, str):
            raise ValueError(f"Column '{col_name}' missing valid 'type' in {contract_path}")
        
        base_type = col_type.split("(")[0].strip().upper()
        if base_type not in VALID_DATA_TYPES:
            raise ValueError(
                f"Column '{col_name}' has unsupported data type '{col_type}' in {contract_path}. "
                f"Allowed: {sorted(list(VALID_DATA_TYPES))}"
            )
        
        min_val = col.get("min_value")
        max_val = col.get("max_value")
        if min_val is not None and max_val is not None:
            if min_val > max_val:
                raise ValueError(
                    f"Column '{col_name}' min_value ({min_val}) exceeds max_value ({max_val}) in {contract_path}"
                )

    # 3. Quality rules validation
    quality_rules = contract.get("quality_rules", [])
    if quality_rules:
        if not isinstance(quality_rules, list):
            raise ValueError(f"'quality_rules' must be a list in {contract_path}")
        for idx, rule_def in enumerate(quality_rules):
            if not isinstance(rule_def, dict) or "rule" not in rule_def:
                raise ValueError(f"Quality rule #{idx} missing 'rule' name in {contract_path}")
            rule_name = rule_def["rule"]
            if rule_name not in VALID_QUALITY_RULES:
                raise ValueError(
                    f"Quality rule '{rule_name}' is not recognized in {contract_path}. "
                    f"Allowed: {sorted(list(VALID_QUALITY_RULES))}"
                )

    return True


def load_contract(contract_path: str) -> dict:
    """Load a YAML contract file, validate schema, and return parsed dict.
    
    Args:
        contract_path: Path to the YAML contract file.
        
    Returns:
        Parsed and validated contract dictionary.
    """
    path = Path(contract_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    
    # Set default quality_rules if missing before validation
    if isinstance(contract, dict):
        contract.setdefault("quality_rules", [])

    # Validate contract schema according to data-engineering-agent-skills
    validate_contract_schema(contract, str(contract_path))
    
    return contract


def load_all_contracts(contracts_dir: str) -> list[dict]:
    """Load all YAML contracts from a directory."""
    contracts = []
    for yaml_file in sorted(Path(contracts_dir).glob("*.yaml")):
        contracts.append(load_contract(str(yaml_file)))
    return contracts
