import pandas as pd
import psycopg
import sys
from pathlib import Path
from app.reference_data import find_unmapped_categories, find_unmapped_codes, resolve_category, resolve_town_name
from app.db import get_connection
from datetime import datetime


TARGET_COLUMNS = [
    {"name": "id", "type": "BIGSERIAL PRIMARY KEY", "source_column": None},
    {"name": "town_code", "type": "TEXT", "source_column": "town"},
    {"name": "town_name", "type": "TEXT", "source_column": None},
    {"name": "txn_date", "type": "DATE", "source_column": "date"},
    {"name": "txn_time", "type": "TIME", "source_column": "time"},
    {"name": "txn_at", "type": "TIMESTAMP", "source_column": None},
    {"name": "card_number", "type": "TEXT", "source_column": "card_number"},
    {"name": "category", "type": "TEXT", "source_column": "category"},
    {"name": "category_clean", "type": "TEXT", "source_column": None},
    {"name": "card_holder", "type": "TEXT", "source_column": "card_holder"},
    {"name": "merchant", "type": "TEXT", "source_column": "merchant"},
    {"name": "quantity_litres", "type": "NUMERIC", "source_column": "quantity"},
    {"name": "product", "type": "TEXT", "source_column": "product"},
    {"name": "rate_per_litre", "type": "NUMERIC", "source_column": "rate"},
    {"name": "amount", "type": "NUMERIC", "source_column": "amount"},
    {"name": "transaction_type", "type": "TEXT", "source_column": "type"},
    {"name": "response", "type": "TEXT", "source_column": "response"},
]


def read_csv(csv_path: Path) -> pd.DataFrame:
    """
    Read a CSV file into a pandas DataFrame with all columns as strings and without converting empty strings to NaN.
    """
    return pd.read_csv(csv_path, dtype=str, keep_default_na=False)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names by stripping whitespace, converting to lowercase, and replacing spaces and hyphens with underscores.
    """
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
    return df


def inspect_dataframe(df: pd.DataFrame) -> None:
    """
    Print row count and column names;
    for each column, number of empty values and distinct values;
    for low-cardinality columns(fewer than 40 distinct values), full list of distinct values;
    for "Quantity", "Rate", and "Amount", the shortest and longest string values;
    for "Date", and "Time", five sample raw values.
    """
    print(f"Row count: {len(df)}")
    print(f"Column count: {len(df.columns)}")
    print(f"Column names: {df.columns.tolist()}")
    for col in df.columns:
        empty_count = (df[col] == "").sum()
        distinct_values = df[col].nunique()
        print(f"\nColumn: {col}")
        print(f"  Empty values: {empty_count}")
        print(f"  Distinct values: {distinct_values}")
        if distinct_values < 40:
            print(f"  Distinct values list: {df[col].unique().tolist()}")
        if col in ["quantity", "rate", "amount"]:
            shortest_val = min(df[col].dropna(), key=len)
            longest_val = max(df[col].dropna(), key=len)
            print(f"  Shortest (string, length): {shortest_val, len(shortest_val)}")
            print(f"  Longest (string, length): {longest_val, len(longest_val)}")
        if col in ["date", "time"]:
            sample_values = df[col].dropna().sample(min(5, len(df[col]))).tolist()
            print(f"  Sample values: {sample_values}")


def _convert_series(series: pd.Series, column_name: str, converter) -> pd.Series:
    """
    Apply converter to every value in series. If converter raises for any value,
    re-raise as a ValueError naming the column, row number, and offending value.
    """
    converted = []
    for row_number, value in series.items():
        try:
            converted.append(converter(value))
        except Exception as exc:
            raise ValueError(
                f"Failed to convert column '{column_name}' at row {row_number}: value {value!r} ({exc})"
            ) from exc
    return pd.Series(converted, index=series.index)


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert an all-text DataFrame with normalised source column names into a
    DataFrame with proper Python/pandas types and final column names.
    """
    result = pd.DataFrame(index=df.index)

    result["town_code"] = _convert_series(df["town"], "town_code", lambda v: v.strip())
    result["town_name"] = _convert_series(result["town_code"], "town_name", resolve_town_name)

    result["category"] = _convert_series(df["category"], "category", lambda v: v.strip())
    result["category_clean"] = _convert_series(result["category"], "category_clean", lambda v: resolve_category(v.strip()))

    result["txn_date"] = _convert_series(
        df["date"],
        "txn_date",
        lambda v: pd.to_datetime(v, format="%d-%b-%Y", errors="raise").date(),
    )
    result["txn_time"] = _convert_series(
        df["time"],
        "txn_time",
        lambda v: pd.to_datetime(v, errors="raise").time(),
    )

    txn_at_values = []
    for row_number, date_value, time_value in zip(result.index, result["txn_date"], result["txn_time"]):
        try:
            txn_at_values.append(datetime.combine(date_value, time_value))
        except Exception as exc:
            raise ValueError(
                f"Failed to convert column 'txn_at' at row {row_number}: "
                f"value {(date_value, time_value)!r} ({exc})"
            ) from exc
    result["txn_at"] = pd.Series(txn_at_values, index=result.index)

    result["card_number"] = _convert_series(df["card_number"], "card_number", lambda v: v.strip())

    result["quantity_litres"] = _convert_series(
        df["quantity"], "quantity_litres", lambda v: pd.to_numeric(v.replace(",", ""), errors="raise")
    )
    result["rate_per_litre"] = _convert_series(
        df["rate"], "rate_per_litre", lambda v: pd.to_numeric(v.replace(",", ""), errors="raise")
    )
    result["amount"] = _convert_series(
        df["amount"], "amount", lambda v: pd.to_numeric(v.replace(",", ""), errors="raise")
    )

    handled_source_columns = {"town", "category", "date", "time", "card_number", "quantity", "rate", "amount", "type"}
    for column in TARGET_COLUMNS:
        source_column = column["source_column"]
        if source_column in handled_source_columns or source_column not in df.columns:
            continue
        result[column["name"]] = _convert_series(df[source_column], column["name"], lambda v: v.strip())

    result["transaction_type"] = _convert_series(df["type"], "transaction_type", lambda v: v.strip())

    return result


def run_quality_checks(df: pd.DataFrame) -> None:
    """
    Run quality checks on the DataFrame and print warnings for any issues found.
    """
    # Unmapped town codes. Print a warning for each unmapped town code.
    unmapped_codes = find_unmapped_codes(df["town_code"].unique())
    if unmapped_codes:
        print(f"Warning: Unmapped town codes found: {unmapped_codes}")
    # Arithmetic consistency check: quantity * rate should equal amount. Allow a small tolerance for floating-point errors.
    arithmetic_issues = df[abs(df["quantity_litres"] * df["rate_per_litre"] - df["amount"]) > 1.0]
    if not arithmetic_issues.empty:
        print(f"Warning: Arithmetic consistency issues found in {len(arithmetic_issues)} rows.")
    # Print the earliest and latest transaction dates in the dataset.
    earliest_txn_date = df["txn_at"].min()
    latest_txn_date = df["txn_at"].max()
    print(f"Date range: {earliest_txn_date} to {latest_txn_date}")
    # Check for negative or zero values in quantity, rate, or amount. Print a warning if any are found.
    negative_values = df[(df["quantity_litres"] <= 0) | (df["rate_per_litre"] <= 0) | (df["amount"] <= 0)]
    if not negative_values.empty:
        print(f"Warning: Negative or zero values found in {len(negative_values)} rows.")
    # Check for duplicate rows across all original columns.
    duplicate_rows = df[df.duplicated(keep=False)]
    if not duplicate_rows.empty:
        print(f"Warning: Duplicate rows found in {len(duplicate_rows)} rows.")
    # Check for distinct values in category and category_clean columns, and print a warning if any unmapped category values are found.
    distinct_categories = df["category"].nunique()
    distinct_clean_categories = df["category_clean"].nunique()
    print(f"Distinct category values: {distinct_categories}")
    print(f"Distinct category_clean values: {distinct_clean_categories}")
    unmapped_categories = find_unmapped_categories(df["category"].unique())
    if len(unmapped_categories) > 0:
        print(f"Warning: Unmapped category values found: {unmapped_categories}")


def create_table(conn: psycopg.Connection, table_name: str, drop_if_exists: bool) -> None:
    """
    Create a table in the database with the specified name and columns defined in TARGET_COLUMNS.
    If drop_if_exists is True, drop the table if it already exists before creating it.
    """
    with conn.cursor() as cur:
        if drop_if_exists:
            cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        columns_definitions = ", ".join(f"{col['name']} {col['type']}" for col in TARGET_COLUMNS)
        cur.execute(f"CREATE TABLE {table_name} ({columns_definitions});"
    )


def insert_rows(conn: psycopg.Connection, table_name: str, df: pd.DataFrame) -> None:
    """
    Insert rows from the DataFrame using COPY command for efficiency.
    If it fails, fall back to executemany for each row.
    """
    with conn.cursor() as cur:
        try:
            # Use COPY for bulk insert
            with cur.copy(f"COPY {table_name} ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)") as copy:
                df.to_csv(copy, index=False, header=True)
            print(f"Inserted {len(df)} rows into {table_name} using COPY.")
        except Exception as e:
            print(f"COPY failed: {e}. Falling back to executemany.")
            # Fallback to executemany for each row
            columns = ", ".join(df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            cur.executemany(insert_query, df.values.tolist())
            print(f"Inserted {len(df)} rows into {table_name} using executemany.")


def verify_load(conn: psycopg.Connection, table_name: str, expected_count: int) -> None:
    """
    Verify that the number of rows in the specified table matches the expected count.
    Raise an exception if the counts do not match.
    """
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
        actual_count = cur.fetchone()["count"]
        if actual_count != expected_count:
            raise ValueError(f"Row count mismatch: expected {expected_count}, got {actual_count}")


def main():
    # Ensure a file path argument was provided
    if len(sys.argv) < 2:
        print("Error: Please provide the CSV file path.")
        sys.exit(1)

    # Read the CSV
    csv_path = Path(sys.argv[1])
    df = read_csv(csv_path)
    # Normalise column names
    df = normalize_column_names(df)
    # Inspect and print
    inspect_dataframe(df)
    # Convert types
    df = convert_types(df)
    # Run quality checks
    run_quality_checks(df)
    # Open a connection
    with get_connection() as conn:
        # Create the table
        table_name = "july_transactions_2026"
        create_table(conn, table_name, drop_if_exists=True)
        # Insert the rows
        insert_rows(conn, table_name, df)
        # Verify
        verify_load(conn, table_name, len(df))


if __name__ == "__main__":
    main()

