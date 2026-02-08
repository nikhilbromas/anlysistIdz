"""
Load DB connection settings from environment. No secrets in code.
"""
import os
from dotenv import load_dotenv

load_dotenv()

MSSQL_SERVER = os.getenv("MSSQL_SERVER", "")
MSSQL_PORT = os.getenv("MSSQL_PORT", "1435")
MSSQL_USER = os.getenv("MSSQL_USER", "")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD", "")
MSSQL_DATABASE = os.getenv("MSSQL_DATABASE", "fiesSaas1971")
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")


def get_connection_string():
    """Build pyodbc connection string from env vars."""
    return (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER},{MSSQL_PORT};"
        f"DATABASE={MSSQL_DATABASE};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PASSWORD};"
    )
