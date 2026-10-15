import sys; sys.stdout.reconfigure(encoding='utf-8')
import duckdb

from pathlib import Path
DB_PATH = str(Path(__file__).resolve().parent.parent / 'data' / 'warehouse.duckdb')
con = duckdb.connect(DB_PATH, read_only=True)

print('=== SCHEMA SUMMARY ===')
schemas = con.execute(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') "
    "ORDER BY table_schema, table_name"
).fetchdf()
print(schemas.to_string(index=False))

print('\n=== GOLD: revenue_by_nation (sample) ===')
gold = con.execute('SELECT * FROM gold.gold_revenue_by_nation LIMIT 10').fetchdf()
print(gold.to_string(index=False))

print('\n=== GOLD: order_priority_summary (sample) ===')
prio = con.execute('SELECT * FROM gold.gold_order_priority_summary LIMIT 10').fetchdf()
print(prio.to_string(index=False))

print('\n=== ROW COUNTS ===')
for tbl in [
    'source.orders', 'source.lineitem', 'source.customer',
    'bronze.bronze_orders', 'bronze.bronze_lineitem',
    'silver.silver_orders', 'silver.silver_lineitem',
    'gold.gold_revenue_by_nation', 'gold.gold_order_priority_summary',
]:
    cnt = con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
    print(f'  {tbl}: {cnt:,} rows')

con.close()
