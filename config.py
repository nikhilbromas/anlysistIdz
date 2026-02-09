"""
Load DB connection settings from environment. No secrets in code.

There are two logical databases:
- Auth DB: central authentication / company registry
- POS DB: the active company database used by the dashboard

By default the POS DB comes from env vars. After login and company
selection, the active POS DB can be overridden per-process using
`set_active_company_connection`.
"""
import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# ── Default POS DB (restaurant) ─────────────────────────────────────────────
MSSQL_SERVER = os.getenv("MSSQL_SERVER", "")
MSSQL_PORT = os.getenv("MSSQL_PORT", "1435")
MSSQL_USER = os.getenv("MSSQL_USER", "")
MSSQL_PASSWORD = os.getenv("MSSQL_PASSWORD", "")
MSSQL_DATABASE = os.getenv("MSSQL_DATABASE", "fiesSaas1971")
MSSQL_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

# ── Auth DB (central user/company registry) ─────────────────────────────────
# If not provided, falls back to the main MSSQL_* settings above.
AUTH_MSSQL_SERVER = os.getenv("AUTH_MSSQL_SERVER", MSSQL_SERVER)
AUTH_MSSQL_PORT = os.getenv("AUTH_MSSQL_PORT", MSSQL_PORT)
AUTH_MSSQL_USER = os.getenv("AUTH_MSSQL_USER", MSSQL_USER)
AUTH_MSSQL_PASSWORD = os.getenv("AUTH_MSSQL_PASSWORD", MSSQL_PASSWORD)
AUTH_MSSQL_DATABASE = os.getenv("AUTH_MSSQL_DATABASE", MSSQL_DATABASE)
AUTH_MSSQL_DRIVER = os.getenv("AUTH_MSSQL_DRIVER", MSSQL_DRIVER)

# ── In-memory override for the active POS DB (set after login) ─────────────
ACTIVE_DB_OVERRIDE: Optional[Dict[str, Any]] = None


def set_active_company_connection(
    server: str,
    database: str,
    user: str,
    password: str,
    port: Optional[str] = None,
    driver: Optional[str] = None,
) -> None:
    """
    Override the active POS DB connection at runtime (after login).

    This does NOT change env vars; it only affects this Python process.
    """
    global ACTIVE_DB_OVERRIDE
    ACTIVE_DB_OVERRIDE = {
        "server": server or MSSQL_SERVER,
        "database": database or MSSQL_DATABASE,
        "user": user or MSSQL_USER,
        "password": password or MSSQL_PASSWORD,
        "port": port or MSSQL_PORT,
        "driver": driver or MSSQL_DRIVER,
    }


def clear_active_company_connection() -> None:
    """Reset to the default POS DB from environment variables."""
    global ACTIVE_DB_OVERRIDE
    ACTIVE_DB_OVERRIDE = None


def get_connection_string() -> str:
    """
    Build pyodbc connection string for the active POS DB.

    If `set_active_company_connection` has been called, that override is
    used; otherwise env-based defaults are used.
    """
    if ACTIVE_DB_OVERRIDE:
        server = ACTIVE_DB_OVERRIDE["server"]
        port = ACTIVE_DB_OVERRIDE["port"]
        user = ACTIVE_DB_OVERRIDE["user"]
        password = ACTIVE_DB_OVERRIDE["password"]
        database = ACTIVE_DB_OVERRIDE["database"]
        driver = ACTIVE_DB_OVERRIDE["driver"]
    else:
        server = MSSQL_SERVER
        port = MSSQL_PORT
        user = MSSQL_USER
        password = MSSQL_PASSWORD
        database = MSSQL_DATABASE
        driver = MSSQL_DRIVER

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
    )


def get_auth_connection_string() -> str:
    """Build pyodbc connection string for the central auth DB."""
    return (
        f"DRIVER={{{AUTH_MSSQL_DRIVER}}};"
        f"SERVER={AUTH_MSSQL_SERVER},{AUTH_MSSQL_PORT};"
        f"DATABASE={AUTH_MSSQL_DATABASE};"
        f"UID={AUTH_MSSQL_USER};"
        f"PWD={AUTH_MSSQL_PASSWORD};"
    )
