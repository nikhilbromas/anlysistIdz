"""
Restaurant Management DB queries — re-export hub.

Split into:
  queries_sales.py    — Sales, service charge, orders, segments
  queries_payments.py — Payment mode, split payments, currency, SP
  queries_stock.py    — Stock movement (20+ UNION ALL blocks)

All SQL_* constants are re-exported here so existing code
(`from db import queries; queries.SQL_SALES_SUMMARY`) works unchanged.
"""

# ---------------------------------------------------------------------------
#  Table / view / SP registry
# ---------------------------------------------------------------------------
TABLES = [
    "aShops",
    "LOsPosHeader",
    "LOsPosDetail",
    "LOsPosOthercharges",
    "RestaurantServiceTaxTransaction",
    "OrderHeader",
    "OrderDetails",
    "IngredientDetails",
    "aItem",
    "aPackingType",
    "aPackingTypeCapacityDetail",
    "aAccountMaster",
    "ASegmentMaster",
    "aCurrencyMaster",
    "PoshPaymentDetails",
    "aCustomerMaster",
    "losShopItemShipmentDetail",
    "DenominationHeader",
    "DenominationDetail",
    "DenominationEntry",
    "aCounterMaster",
    "Users",
]

VIEWS = []

STORED_PROCEDURES = {
    "spGetPosAmtDetailForReportFB": [],
}

# ---------------------------------------------------------------------------
#  Re-export all SQL constants from sub-modules
# ---------------------------------------------------------------------------
from db.queries_sales import (          # noqa: E402, F401
    SQL_RESTAURANT_SHOPS,
    SQL_SALES_SUMMARY,
    SQL_SALES_BILL_LEVEL,
    SQL_SALES_DETAIL,
    SQL_SERVICE_CHARGE,
    SQL_ORDER_INGREDIENT,
    SQL_ORDER_HEADER,
    SQL_ORDER_DETAILS,
    SQL_SEGMENT_SALES,
    SQL_CUSTOMER_PROFITABILITY,
    SQL_SEGMENT_ITEM_PRICING,
)

from db.queries_payments import (       # noqa: E402, F401
    SQL_PAYMENT_MODE,
    SQL_CURRENCY_MASTER,
    SQL_SPLIT_PAYMENT,
    SQL_SP_FB_POS_AMT,
    SQL_SESSIONS,
    SQL_GST_SALES,
    SQL_DENOMINATION_DETAIL,
    SQL_DAY_END_SALES,
)

from db.queries_stock import (          # noqa: E402, F401
    SQL_STOCK_MOVEMENT,
)


# ---------------------------------------------------------------------------
#  Helper builders
# ---------------------------------------------------------------------------
def sql_for_table(table_name: str) -> str:
    return f"SELECT * FROM [{table_name}]"

def sql_for_view(view_name: str) -> str:
    return f"SELECT * FROM [{view_name}]"

def sp_call_sql(sp_name: str, params: dict) -> str:
    if not params:
        return f"EXEC [{sp_name}]"
    placeholders = ", ".join("?" for _ in params)
    return f"EXEC [{sp_name}] {placeholders}"
