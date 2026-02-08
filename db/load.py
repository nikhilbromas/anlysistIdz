"""
Load restaurant data from DB. One function per dataset.
Uses cursor-based loading to avoid pandas SQLAlchemy warning.
Converts Decimal columns to float so charts and aggregations work.
"""
import pandas as pd
import numpy as np
from decimal import Decimal
from db.connection import get_connection
from db import queries
import warnings

warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")


def _convert_decimals(df: pd.DataFrame) -> pd.DataFrame:
    """Convert any column containing Decimal values to float64."""
    for col in df.columns:
        if df[col].dtype == object and len(df) > 0:
            sample = df[col].dropna().head(5)
            if len(sample) > 0 and isinstance(sample.iloc[0], Decimal):
                df[col] = df[col].apply(lambda x: float(x) if x is not None else np.nan)
    return df


def _safe_load(sql: str) -> pd.DataFrame:
    """Execute SQL via cursor and return DataFrame. Returns empty on error."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            df = pd.DataFrame.from_records(rows, columns=columns)
            df = _convert_decimals(df)
            return df
    except Exception as e:
        print(f"[DB] query error: {e}")
        return pd.DataFrame()


# ---- individual loaders ----

def load_restaurant_shops() -> pd.DataFrame:
    """Restaurant shops (aShops.futurevarchar = 'f')."""
    return _safe_load(queries.SQL_RESTAURANT_SHOPS)


def load_sales_summary() -> pd.DataFrame:
    """Daily sales aggregated by shop and date."""
    return _safe_load(queries.SQL_SALES_SUMMARY)


def load_sales_bill_level() -> pd.DataFrame:
    """Bill-level sales with billid and counterid for session filtering."""
    return _safe_load(queries.SQL_SALES_BILL_LEVEL)


def load_sales_detail() -> pd.DataFrame:
    """Item-level POS sales detail."""
    return _safe_load(queries.SQL_SALES_DETAIL)


def load_service_charge() -> pd.DataFrame:
    """Service charge report."""
    return _safe_load(queries.SQL_SERVICE_CHARGE)


def load_order_ingredient() -> pd.DataFrame:
    """Order-level ingredient consumption and cost."""
    return _safe_load(queries.SQL_ORDER_INGREDIENT)


def load_order_header() -> pd.DataFrame:
    """Order header records."""
    return _safe_load(queries.SQL_ORDER_HEADER)


def load_order_details() -> pd.DataFrame:
    """Order detail line items."""
    return _safe_load(queries.SQL_ORDER_DETAILS)


def load_payment_mode() -> pd.DataFrame:
    """Payment mode analysis."""
    return _safe_load(queries.SQL_PAYMENT_MODE)


def load_segment_sales() -> pd.DataFrame:
    """Segment-wise sales analysis."""
    return _safe_load(queries.SQL_SEGMENT_SALES)


def load_sp_fb_pos_amt() -> pd.DataFrame:
    """Execute spGetPosAmtDetailForReportFB and return result set."""
    return _safe_load(queries.SQL_SP_FB_POS_AMT)


def load_currencies() -> pd.DataFrame:
    """Currency master (CurrencyID, CurrencyName, Symbol)."""
    return _safe_load(queries.SQL_CURRENCY_MASTER)


def load_split_payments() -> pd.DataFrame:
    """Split payment details per bill."""
    return _safe_load(queries.SQL_SPLIT_PAYMENT)


def load_stock_movement() -> pd.DataFrame:
    """Full stock movement (20+ types). mode=1 in, mode=-1 out."""
    return _safe_load(queries.SQL_STOCK_MOVEMENT)


def load_customer_profitability() -> pd.DataFrame:
    """Customer-wise line-level revenue, cost, profit data."""
    return _safe_load(queries.SQL_CUSTOMER_PROFITABILITY)


def load_segment_item_pricing() -> pd.DataFrame:
    """Segment-wise item selling prices for menu items."""
    return _safe_load(queries.SQL_SEGMENT_ITEM_PRICING)


def load_sessions() -> pd.DataFrame:
    """Till sessions (open/close pairs)."""
    return _safe_load(queries.SQL_SESSIONS)


def load_gst_sales() -> pd.DataFrame:
    """GST sales from vwCAshSalesGSTSeparately."""
    return _safe_load(queries.SQL_GST_SALES)


def load_denomination_detail() -> pd.DataFrame:
    """Denomination cash counting per session."""
    return _safe_load(queries.SQL_DENOMINATION_DETAIL)


def load_day_end_sales() -> pd.DataFrame:
    """Day-end bill-level report with split payments, tax, service charge, returns."""
    return _safe_load(queries.SQL_DAY_END_SALES)
