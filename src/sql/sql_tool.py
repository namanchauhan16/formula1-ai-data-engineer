from pathlib import Path
import re

import duckdb
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


GOLD_TABLES = {
    "dim_drivers": PROJECT_ROOT / "data" / "dim_drivers",
    "dim_constructors": PROJECT_ROOT / "data" / "dim_constructors",
    "dim_races": PROJECT_ROOT / "data" / "dim_races",
    "fact_results": PROJECT_ROOT / "data" / "fact_results",
}


class SQLQuery(BaseModel):
    sql: str = Field(
        description="A single read-only DuckDB SQL SELECT query"
    )


def get_schema():
    con = duckdb.connect()

    con.execute("INSTALL delta")
    con.execute("LOAD delta")

    schema_parts = []

    for table_name, table_path in GOLD_TABLES.items():

        result = con.execute(
            f"""
            DESCRIBE SELECT *
            FROM delta_scan('{table_path.as_posix()}')
            """
        ).fetchall()

        schema_parts.append(f"TABLE: {table_name}")

        for row in result:
            column_name = row[0]
            data_type = row[1]

            schema_parts.append(
                f"  - {column_name}: {data_type}"
            )

        schema_parts.append("")

    con.close()

    return "\n".join(schema_parts)


RELATIONSHIPS = """
Known relationships:

fact_results.driver_id
    -> dim_drivers.driver_id

fact_results.constructor_id
    -> dim_constructors.constructor_id

fact_results.season + fact_results.round
    -> dim_races.season + dim_races.round
"""


llm = ChatOpenAI(
    model="gpt-5.6-luna",
    temperature=0
).with_structured_output(SQLQuery)


def generate_sql(question: str) -> str:

    schema = get_schema()

    prompt = f"""
    You are a SQL generation assistant for a Formula 1 analytics database.

    Generate exactly ONE read-only DuckDB SQL query.

    Rules:
    - Use only the tables and columns provided in the schema.
    - Do not invent tables or columns.
    - Only generate SELECT or WITH queries.
    - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
    REPLACE, TRUNCATE, GRANT, or REVOKE.
    - Use the provided relationships when joins are required.
    - Match database values using their actual stored values.
    - For session_type, valid values are 'RACE' and 'SPRINT'.
    - For text comparisons, use case-insensitive matching when appropriate.

    DATABASE SCHEMA:
    {schema}

    {RELATIONSHIPS}

    USER QUESTION:
    {question}
    """

    response = llm.invoke(prompt)

    return response.sql.strip()


def validate_sql(sql: str) -> None:

    sql = sql.strip()

    if not sql:
        raise ValueError("Generated SQL is empty.")

    sql_without_trailing_semicolon = sql.rstrip(";").strip()

    if ";" in sql_without_trailing_semicolon:
        raise ValueError("Multiple SQL statements are not allowed.")

    normalized_sql = sql_without_trailing_semicolon.lower()

    if not (
        normalized_sql.startswith("select")
        or normalized_sql.startswith("with")
    ):
        raise ValueError(
            "Only SELECT or WITH queries are allowed."
        )

    forbidden_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "grant",
        "revoke",
    ]

    for keyword in forbidden_keywords:

        if re.search(
            rf"\b{re.escape(keyword)}\b",
            normalized_sql
        ):
            raise ValueError(
                f"Forbidden SQL operation detected: {keyword}"
            )


def execute_sql(sql: str):

    validate_sql(sql)

    con = duckdb.connect()

    con.execute("INSTALL delta")
    con.execute("LOAD delta")

    # Expose Delta tables as logical DuckDB views
    for table_name, table_path in GOLD_TABLES.items():

        con.execute(
            f"""
            CREATE OR REPLACE VIEW {table_name} AS
            SELECT *
            FROM delta_scan('{table_path.as_posix()}')
            """
        )

    # Check whether DuckDB can understand the query
    con.execute(f"EXPLAIN {sql}")

    result = con.execute(sql)

    columns = [
        column[0]
        for column in result.description
    ]

    rows = result.fetchall()

    con.close()

    return columns, rows


@tool
def query_f1_data(question: str) -> str:
    """
    Answer questions that require structured Formula 1 data
    by generating and executing read-only SQL against the
    Gold analytical tables.

    If the generated SQL fails, return the database error so
    the agent can correct the query.

    """
    
    sql = generate_sql(question)

    try:
        columns, rows = execute_sql(sql)

    except Exception as error:

        return (
            "The generated SQL could not be executed.\n\n"
            f"Generated SQL:\n{sql}\n\n"
            f"Database error:\n{error}"
        )

    if not rows:
        return (
            f"No data was found for the question.\n\n"
            f"Generated SQL:\n{sql}"
        )

    output = [
        f"Columns: {columns}",
        "",
        "Results:"
    ]

    for row in rows:
        output.append(str(row))

    return "\n".join(output)