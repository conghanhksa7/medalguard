"""Load and parse MedalGuard YAML contract definitions."""
import yaml
from pathlib import Path


def load_contract(contract_path: str) -> dict:
    """Load a YAML contract file and return parsed dict.
    
    Args:
        contract_path: Path to the YAML contract file.
        
    Returns:
        Parsed contract dictionary with keys: table, source_table, columns, quality_rules.
    """
    path = Path(contract_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    
    # Validate required fields
    required = ["table", "source_table", "columns"]
    for field in required:
        if field not in contract:
            raise ValueError(f"Contract missing required field: '{field}' in {contract_path}")
    
    # Set defaults
    contract.setdefault("quality_rules", [])
    
    return contract


def load_all_contracts(contracts_dir: str) -> list[dict]:
    """Load all YAML contracts from a directory."""
    contracts = []
    for yaml_file in sorted(Path(contracts_dir).glob("*.yaml")):
        contracts.append(load_contract(str(yaml_file)))
    return contracts
