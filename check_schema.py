import sqlite3

conn = sqlite3.connect('/home/hadoopminhquang/spotify_gold.db')

print("Tables in database:")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  - {t[0]}")

print("\n" + "=" * 80)
for table in tables:
    table_name = table[0]
    print(f"\nTable: {table_name}")
    columns = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
    print("Columns:", [col[1] for col in columns])

conn.close()
