import sys

from app.prompt_builder import build_prompt, estimate_tokens
from app.schema_reader import get_table_schema


def main():
# Ensure a question was was provided
    if len(sys.argv) < 2:
        print("Error: Please ask a question.")
        sys.exit(1)

    question = sys.argv[1]
    schema = get_table_schema("july_transactions_2026")
    date = "2026-08-23"
    system_prompt, user_prompt = build_prompt(question, schema, date)
    system_prompt_token_est = estimate_tokens(system_prompt)
    user_prompt_token_est = estimate_tokens(user_prompt)

    print("--------system prompt--------")
    print(f"Token usage: {system_prompt_token_est}")
    print(system_prompt)

    print("--------user prompt--------")
    print(f"Token usage: {user_prompt_token_est}")
    print(user_prompt)


if __name__ == "__main__":
    main()
    
