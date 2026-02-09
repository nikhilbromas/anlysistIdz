"""
Lightweight DB helper with a single `execute_query` function.

Supports:
- POS DB (default) via `config.get_connection_string()`
- Auth DB via `config.get_auth_connection_string()` when `use_auth_db=True`

Parameters are passed as a dict with T-SQL style names (e.g. @email);
this helper rewrites them to positional `?` placeholders for pyodbc.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import pyodbc

from config import get_connection_string, get_auth_connection_string


def _prepare_sql_and_params(sql: str, params: Optional[Dict[str, Any]]) -> Tuple[str, Tuple[Any, ...]]:
    """
    Replace @name-style parameters with ? for pyodbc and return ordered values.

    This is a simple textual replacement and assumes parameter names do not
    appear inside string literals. Good enough for our short auth queries.
    """
    if not params:
        return sql, ()

    ordered_keys: List[str] = []
    rewritten = sql
    for key, value in params.items():
        placeholder = f"@{key}"
        if placeholder in rewritten:
            rewritten = rewritten.replace(placeholder, "?")
            ordered_keys.append(key)

    ordered_values: Tuple[Any, ...] = tuple(params[k] for k in ordered_keys)
    return rewritten, ordered_values


def execute_query(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    use_auth_db: bool = False,
) -> List[Dict[str, Any]]:
    """
    Execute a read-only query and return a list of row dicts.

    Args:
        sql: T-SQL statement, optionally with @param style placeholders.
        params: dict of parameter values keyed by name without @.
        use_auth_db: if True, runs against the auth DB; otherwise POS DB.
    """
    conn_str = get_auth_connection_string() if use_auth_db else get_connection_string()
    sql_final, values = _prepare_sql_and_params(sql, params)

    rows: List[Dict[str, Any]] = []
    with pyodbc.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_final, values)
            desc = cur.description
            if not desc:
                return []
            cols: Iterable[str] = [c[0] for c in desc]
            for rec in cur.fetchall():
                rows.append({col: val for col, val in zip(cols, rec)})
    return rows

