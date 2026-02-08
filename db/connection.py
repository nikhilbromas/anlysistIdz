"""
MSSQL connection helper. Use as context manager to ensure connection is closed.
"""
import pyodbc
from contextlib import contextmanager
from config import get_connection_string


@contextmanager
def get_connection():
    """Yield a pyodbc connection; closes on exit."""
    conn = None
    try:
        conn = pyodbc.connect(get_connection_string())
        yield conn
    finally:
        if conn:
            conn.close()
