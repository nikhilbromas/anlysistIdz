"""
Restaurant-specific feature engineering for ML models.
Works on the sales_summary and order_ingredient DataFrames.
"""
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
#  Sales forecasting features  (from sales_summary)
# ---------------------------------------------------------------------------
def prepare_sales_features(df: pd.DataFrame):
    """
    Target: total_amount (daily revenue)
    Features: day-of-week, day-of-month, month, shopid,
              lagged values, rolling averages.
    Returns (X, y, feature_names) or (None, None, []).
    """
    if df is None or df.empty or len(df) < 7:
        return None, None, []

    df = df.copy()
    df["billdate"] = pd.to_datetime(df["billdate"])
    df = df.sort_values("billdate")

    # time features
    df["dayofweek"]  = df["billdate"].dt.dayofweek
    df["day"]        = df["billdate"].dt.day
    df["month"]      = df["billdate"].dt.month
    df["weekofyear"] = df["billdate"].dt.isocalendar().week.astype(int)

    # aggregate per date (across shops) for lag/rolling
    daily = (
        df.groupby("billdate")
        .agg(total_amount=("total_amount", "sum"),
             total_bills=("total_bills", "sum"))
        .reset_index()
        .sort_values("billdate")
    )
    daily["lag_1"]   = daily["total_amount"].shift(1)
    daily["lag_7"]   = daily["total_amount"].shift(7)
    daily["roll_7"]  = daily["total_amount"].rolling(7).mean()
    daily["roll_30"] = daily["total_amount"].rolling(30).mean()

    # time features on daily grain
    daily["dayofweek"]  = daily["billdate"].dt.dayofweek
    daily["day"]        = daily["billdate"].dt.day
    daily["month"]      = daily["billdate"].dt.month
    daily["weekofyear"] = daily["billdate"].dt.isocalendar().week.astype(int)

    daily.dropna(inplace=True)
    if daily.empty:
        return None, None, []

    feature_cols = ["dayofweek", "day", "month", "weekofyear",
                    "total_bills", "lag_1", "lag_7", "roll_7", "roll_30"]
    X = daily[feature_cols].values
    y = daily["total_amount"].values
    return X, y, feature_cols


# ---------------------------------------------------------------------------
#  Ingredient demand features  (from order_ingredient)
# ---------------------------------------------------------------------------
def prepare_ingredient_features(df: pd.DataFrame):
    """
    Target: cashsales (ingredient qty consumed per day)
    Features: dayofweek, day, month, costprice, item-level lags.
    Returns (X, y, feature_names) or (None, None, []).
    """
    if df is None or df.empty or len(df) < 7:
        return None, None, []

    df = df.copy()
    df["sdate"] = pd.to_datetime(df["sdate"])
    df = df.sort_values("sdate")

    # aggregate by date + item
    daily = (
        df.groupby(["sdate", "itemid"])
        .agg(cashsales=("cashsales", "sum"),
             costprice=("costprice", "mean"))
        .reset_index()
        .sort_values("sdate")
    )
    daily["dayofweek"] = daily["sdate"].dt.dayofweek
    daily["day"]       = daily["sdate"].dt.day
    daily["month"]     = daily["sdate"].dt.month
    daily["lag_1"]     = daily.groupby("itemid")["cashsales"].shift(1)
    daily["lag_7"]     = daily.groupby("itemid")["cashsales"].shift(7)

    daily.dropna(inplace=True)
    if daily.empty:
        return None, None, []

    feature_cols = ["dayofweek", "day", "month", "costprice", "lag_1", "lag_7"]
    X = daily[feature_cols].values
    y = daily["cashsales"].values
    return X, y, feature_cols


# ---------------------------------------------------------------------------
#  Stock demand features  (from stock_movement, mode=-1 consumption)
# ---------------------------------------------------------------------------
def prepare_stock_features(df: pd.DataFrame):
    """
    Target: daily total qty consumed (mode=-1 records, aggregated per item per day)
    Features: dayofweek, day, month, costprice, item-level lags.
    Returns (X, y, feature_names) or (None, None, []).
    """
    if df is None or df.empty or len(df) < 7:
        return None, None, []

    df = df.copy()
    df["sdate"] = pd.to_datetime(df["sdate"], errors="coerce")
    df["qty"]   = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
    df["costprice"] = pd.to_numeric(df["costprice"], errors="coerce").fillna(0)

    # Only stock out (consumption)
    df = df[df["mode"] == -1].copy()
    if df.empty or len(df) < 7:
        return None, None, []

    df = df.sort_values("sdate")

    # aggregate by date + item
    daily = (
        df.groupby(["sdate", "itemid"])
        .agg(qty=("qty", "sum"),
             costprice=("costprice", "mean"))
        .reset_index()
        .sort_values("sdate")
    )
    daily["dayofweek"] = daily["sdate"].dt.dayofweek
    daily["day"]       = daily["sdate"].dt.day
    daily["month"]     = daily["sdate"].dt.month
    daily["lag_1"]     = daily.groupby("itemid")["qty"].shift(1)
    daily["lag_7"]     = daily.groupby("itemid")["qty"].shift(7)
    daily["roll_7"]    = daily.groupby("itemid")["qty"].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )

    daily.dropna(inplace=True)
    if daily.empty:
        return None, None, []

    feature_cols = ["dayofweek", "day", "month", "costprice", "lag_1", "lag_7", "roll_7"]
    X = daily[feature_cols].values
    y = daily["qty"].values
    return X, y, feature_cols


# ---------------------------------------------------------------------------
#  Generic fallback (works on any numeric DataFrame)
# ---------------------------------------------------------------------------
def prepare_generic_features(df: pd.DataFrame, target_col: str = None):
    """
    Generic feature builder. Uses all numeric cols as features, last one as target.
    """
    if df is None or df.empty or len(df) < 2:
        return None, None, []

    df = df.copy()
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric:
        return None, None, []

    date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    if date_cols:
        df["_dayofweek"] = pd.to_datetime(df[date_cols[0]]).dt.dayofweek
        df["_day"]       = pd.to_datetime(df[date_cols[0]]).dt.day
        numeric += ["_dayofweek", "_day"]

    if target_col and target_col in df.columns:
        y = df[target_col].values
        feature_cols = [c for c in numeric if c != target_col]
    else:
        y = df[numeric[-1]].values
        feature_cols = numeric[:-1]

    if not feature_cols:
        return None, None, []

    X = df[feature_cols].fillna(0).values
    return X, y, feature_cols
