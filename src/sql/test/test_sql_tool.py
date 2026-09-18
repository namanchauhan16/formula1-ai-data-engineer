from ..sql_tool import query_f1_data


result = query_f1_data.invoke(
    "Who won the 2024 British Grand Prix?"
)

print(result)