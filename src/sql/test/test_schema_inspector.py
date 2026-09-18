from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLD_TABLES = {
    "dim_drivers": PROJECT_ROOT / "data" / "dim_drivers",
    "dim_constructors": PROJECT_ROOT / "data" / "dim_constructors",
    "dim_races": PROJECT_ROOT / "data" / "dim_races",
    "fact_results": PROJECT_ROOT / "data" / "fact_results",
}

def get_delta_schema(connection, table_name, table_path):
    path = table_path.as_posix()

    result = connection.execute(
        f"""
        DESCRIBE SELECT *
        FROM delta_scan('{path}')
        """
    ).fetchall()

    print(f"\n=== {table_name} ===")

    for row in result:
        column_name = row[0]
        data_type = row[1]

        print(f"{column_name} : {data_type}")


def main():
    con = duckdb.connect()

    con.execute("INSTALL delta")
    con.execute("LOAD delta")

    for table_name, table_path in GOLD_TABLES.items():
        get_delta_schema(
            con,
            table_name,
            table_path
        )

    con.close()


if __name__ == "__main__":
    main()