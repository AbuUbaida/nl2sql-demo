from dataclasses import dataclass, field
import time

from app.table_metadata import ColumnMetadata, get_table_metadata
from app.db import get_connection, table_exists


@dataclass
class ColumnSchema:
    name: str
    sql_type: str
    nullable: bool
    description: str
    unit: str | None
    distinct_count: int | None
    sample_values: list[str]
    value_range: tuple[str, str] | None

@dataclass
class TableSchema:
    name: str
    description: str
    row_count: int
    columns: list[ColumnSchema]
    notes: list[str]

_schema_cache: dict[str, tuple[TableSchema, float]] = {}
_CACHE_TTL_SECONDS: float = 300.0


def fetch_column_catalog(conn, table_name: str) -> list[dict]:
    """
    Fetches column catalog information for a given table from the database.
    One dict per column: name, data type, nullability, ordinal position.
    """
    query = f"""
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        columns = cursor.fetchall()
    return [
        {
            "name": col["column_name"],
            "sql_type": col["data_type"],
            "nullable": col["is_nullable"] == 'YES',
            "ordinal_position": col["ordinal_position"]
        }
        for col in columns
    ]


def fetch_row_count(conn, table_name: str) -> int:
    """
    Fetches the total number of rows in a given table.
    """
    query = f"SELECT COUNT(*) FROM {table_name};"
    with conn.cursor() as cursor:
        cursor.execute(query)
        count = cursor.fetchone()["count"]
    return count


def simplify_type(pg_type: str) -> str:
    """
    Simplifies PostgreSQL data types to a more general form.
    """
    type_mapping = {
        "character varying": "TEXT",
        "timestamp without time zone": "TIMESTAMP",
        "numeric": "NUMERIC",
        "integer": "BIGINT",
        "date": "DATE",
        "time without time zone": "TIME"
    }
    return type_mapping.get(pg_type.lower(), pg_type.upper())


def fetch_distinct_count(conn, table_name: str, column_name: str) -> int:
    """
    Fetches the number of distinct values in a specific column of a table.
    """
    query = f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name};"
    with conn.cursor() as cursor:
        cursor.execute(query)
        count = cursor.fetchone()["count"]
    return count


def fetch_sample_values(conn, table_name: str, column_name: str, limit: int = 10) -> list[str]:
    """
    Fetches a sample of distinct values from a specific column of a table, most frequent first.
    """
    query = f"""
        SELECT {column_name}
        FROM {table_name}
        GROUP BY {column_name}
        ORDER BY COUNT(*) DESC
        LIMIT {limit};
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        samples = cursor.fetchall()
    return [row[column_name] for row in samples]


def fetch_value_range(conn, table_name: str, column_name: str) -> tuple[str, str] | None:
    """
    Fetches the minimum and maximum values of a specific column in a table.
    Returns None if the column is not suitable for range queries (e.g., text).
    """
    query = f"""
        SELECT MIN({column_name}) AS min_value, MAX({column_name}) AS max_value
        FROM {table_name};
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()
    if result["min_value"] is None or result["max_value"] is None:
        return None
    return (result["min_value"], result["max_value"])


def should_fetch_sample(column_meta: ColumnMetadata, sql_type: str) -> bool:
    """
    Determines whether to fetch sample values for a column based on its metadata and characteristics.
    """
    # If the column is marked as sensitive, we should not fetch samples.
    if column_meta.is_sensitive:
        return False
    if not column_meta.show_samples:
        return False
    if sql_type in ["NUMERIC", "DATE", "TIME", "TIMESTAMP"]:
        return False
    return True


def build_table_schema(conn, table_name: str) -> TableSchema:
    if not table_exists(table_name):
        raise ValueError(f"Table '{table_name}' does not exist in the database.")
    
    table_metadata = get_table_metadata(table_name)
    column_catalog = fetch_column_catalog(conn, table_name)
    row_count = fetch_row_count(conn, table_name)

    column_schemas = []
    for column in column_catalog:
        simplified_column_type = simplify_type(column["sql_type"])
        column_meta = table_metadata.columns.get(
            column["name"],
            ColumnMetadata(
                description="(no description available)",
                is_sensitive=True,
                show_samples=False
            ))
        distinct_count = fetch_distinct_count(conn, table_name, column["name"])
        if should_fetch_sample(column_meta, simplified_column_type):
            sample_values = fetch_sample_values(conn, table_name, column["name"], 10)
            value_range = None
        elif simplified_column_type in ["NUMERIC", "DATE"]:
            value_range = fetch_value_range(conn, table_name, column["name"])
            sample_values = []
        else:
            sample_values = []
            value_range = None

        column_schemas.append(
            ColumnSchema(
                name=column["name"],
                sql_type=simplified_column_type,
                nullable=column["nullable"],
                description=column_meta.description,
                unit=column_meta.unit,
                distinct_count=distinct_count,
                sample_values=sample_values,
                value_range=value_range
            )
        )

    return TableSchema(
        name=table_name,
        description=table_metadata.description,
        row_count=row_count,
        columns=column_schemas,
        notes=table_metadata.notes
    )


def format_samples(values: list[str], distinct_count: int) -> str:
    if not values:
        return ""
    else:
        samples = "Values: "
        samples += ", ".join([f'{value}' for value in values])
        if len(values) < distinct_count:
            samples += f" (showing {len(values)} of {distinct_count})."
        return samples


def format_range(value_range: tuple[str, str] | None) -> str:
    if not value_range:
        return ""
    else:
        min_val, max_val = value_range
        return "Range: " + str(min_val) + " to " + str(max_val) + "."
            

def format_column_line(column: ColumnSchema, name_width: int, type_width: int) -> str:
    col_name_pad = name_width - len(column.name)
    col_name_padded = column.name + " "*col_name_pad

    sql_type_pad = type_width - len(column.sql_type)
    sql_type_padded = column.sql_type + " "*sql_type_pad

    col_comment = column.description
    if column.unit:
        col_comment += f" Unit: {column.unit}."
    if format_samples:
        col_comment += f" {format_samples(column.sample_values, column.distinct_count)}"
    if format_range:
        col_comment += f" {format_range(column.value_range)}"

    col_line_assembled = " "*2 + col_name_padded + sql_type_padded + "-- " + col_comment
    return col_line_assembled


def render_schema_for_prompt(schema: TableSchema) -> str:
    name_width = max(len(col.name) for col in schema.columns) + 2
    type_width = max(len(col.sql_type) for col in schema.columns) + 2

    lines = []
    lines.append(f"Table: {schema.name}")
    lines.append(schema.description)
    lines.append(f"Rows: {schema.row_count:,}")
    lines.append("")

    lines.append("Columns:")
    for col_schema in schema.columns:
        lines.append(format_column_line(col_schema, name_width, type_width))
    lines.append("")

    if schema.notes:
        lines.append("Important notes:")
        for note in schema.notes:
            lines.append(f"  - {note}")

    return "\n".join(lines)


def get_table_schema(table_name: str, force_refresh: bool = False) -> TableSchema:
    curr_time = time.time()

    if not force_refresh and table_name in _schema_cache:
        cached_schema, timestamp = _schema_cache[table_name]
    else:
        cached_schema, timestamp = None, None

    if cached_schema is not None and curr_time-timestamp < _CACHE_TTL_SECONDS:
        schema = cached_schema
    else:
        with get_connection() as conn:
            schema = build_table_schema(conn, table_name)
            _schema_cache[table_name] = (schema, curr_time)

    return schema