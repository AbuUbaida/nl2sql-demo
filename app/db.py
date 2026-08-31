from psycopg.rows import dict_row
from psycopg import connect, Connection
from typing import Generator
from app.config import settings
from contextlib import contextmanager


@contextmanager
def get_connection() -> Generator[Connection]:
    """
    Get a database connection using the configured database URL.
    This function yields a connection object that can be used to interact with the database.
    If the caller block finishes normally, commit the transaction; if an exception occurs, roll back the transaction.
    """
    conn: Connection = connect(conninfo=settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_connection() -> bool:
    """
    Check if the database connection can be established.
    Returns True if the connection is successful, False otherwise.
    """
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
        except Exception:
            return False


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    Returns True if the table exists, False otherwise.
    """
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
                    (table_name,)
                )
                return cur.fetchone()["exists"]
        except Exception:
            return False
