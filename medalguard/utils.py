import re

def quote_identifier(name: str) -> str:
    """Validates and quotes SQL identifiers to prevent SQL injection."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid identifier: {name}")
    return f'"{name}"'

def parse_table_ref(full_name: str) -> tuple[str, str]:
    """Splits 'schema.table' into (schema, table)."""
    parts = full_name.split(".")
    if len(parts) == 1:
        return "main", parts[0]
    return parts[0], parts[1]

def quote_table(full_name: str) -> str:
    """Quotes a full table reference like schema.table."""
    schema, table = parse_table_ref(full_name)
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"
