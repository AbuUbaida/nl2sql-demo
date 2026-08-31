import sys

from app.llm_client import generate_sql
from app.schema_reader import get_table_schema


def main():
# Ensure a question was was provided
    if len(sys.argv) < 2:
        print("Error: Please ask a question.")
        sys.exit(1)

    question = sys.argv[1]
    schema = get_table_schema("july_transactions_2026")
    date = "2026-08-23"
    response = generate_sql(question, schema, date)

    print("Answerable: ", response.answerable)
    print("SQL: ", response.sql)
    print("Explanation: ", response.explanation)
    print("Assumptions: ", response.assumptions)
    print("Confidence: ", response.confidence)
    print("Input tokens: ", response.input_tokens, "Output tokens: ", response.output_tokens)
    print("Cost: ", response.cost_usd)
    print("Latency: ", response.latency_ms)
    print("Refusal reason: ", response.refusal_reason)


if __name__ == "__main__":
    main()
    
