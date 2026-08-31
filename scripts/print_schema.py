import time
from app.schema_reader import get_table_schema, render_schema_for_prompt


def main():
    precall_time = time.time()
    schema = get_table_schema("july_transactions_2026")
    postcall_time = time.time()
    rendered_schema = render_schema_for_prompt(schema)
    token_est = len(rendered_schema)/4
    print(f"Estimated tokens: {token_est}")
    print(f"Time to build the schema: {postcall_time-precall_time} milliseconds")
    print(rendered_schema)


if __name__ == "__main__":
    main()