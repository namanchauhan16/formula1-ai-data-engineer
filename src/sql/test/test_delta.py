from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]

con = duckdb.connect()

# Load Delta Lake extension
con.execute("INSTALL delta")
con.execute("LOAD delta")

gold_tables = {
    "dim_driver": PROJECT_ROOT / "data" / "dim_drivers",
    "dim_constructor": PROJECT_ROOT / "data" / "dim_constructors",
    "dim_race": PROJECT_ROOT / "data" / "dim_races",
    "fact_results": PROJECT_ROOT / "data" / "fact_results",
}


for table_name, table_path in gold_tables.items():
    print(f"\n===== {table_name} =====")

    result = con.execute(
        f"""
        SELECT *
        FROM delta_scan('{table_path.as_posix()}')
        LIMIT 5
        """
    )

    print("Columns:")
    print([column[0] for column in result.description])

    print("\nRows:")
    for row in result.fetchall():
        print(row)


con.close()