"""Generate TPC-H benchmark data in DuckDB source schema."""
import duckdb
import os
import sys


def generate_tpch(db_path: str, scale_factor: float = 1.0):
    """Generate TPC-H data in DuckDB source schema.
    
    Args:
        db_path: Path to DuckDB database file.
        scale_factor: TPC-H scale factor.
            - 0.01 (~10MB, for quick testing)
            - 0.1  (~100MB, for development)
            - 1.0  (~1GB, for final experiments)
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    con = duckdb.connect(db_path)
    
    # Create source schema (simulates production OLTP database)
    con.execute("CREATE SCHEMA IF NOT EXISTS source")
    
    # Install and load TPC-H extension
    con.execute("INSTALL tpch; LOAD tpch;")
    
    # Generate all 8 TPC-H tables in source schema
    print(f"Generating TPC-H data (SF={scale_factor})...")
    con.execute(f"CALL dbgen(sf={scale_factor}, schema='source', overwrite=true)")
    
    # Verify generated tables
    print("\nGenerated tables:")
    print("-" * 45)
    tables = con.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'source'
        ORDER BY table_name
    """).fetchall()
    
    total_rows = 0
    for (table_name,) in tables:
        count = con.execute(
            f"SELECT COUNT(*) FROM source.{table_name}"
        ).fetchone()[0]
        total_rows += count
        print(f"  source.{table_name:<15} {count:>12,} rows")
    
    print("-" * 45)
    print(f"  {'TOTAL':<15} {total_rows:>12,} rows")
    
    con.close()
    print(f"\nDatabase saved to: {os.path.abspath(db_path)}")
    print("TPC-H data generated successfully!")


if __name__ == "__main__":
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "warehouse.duckdb"
    )
    
    # Use small scale factor for development, SF=1 for final experiments
    sf = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
    generate_tpch(db_path, scale_factor=sf)
