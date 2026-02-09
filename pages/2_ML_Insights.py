"""
ML Insights — Sales Forecasting, Ingredient Demand, Stock Demand Prediction.
"""
import pandas as pd
import numpy as np
import streamlit as st

from auth.ui import require_login_and_company
from data_loader import get_sales_summary, get_order_ingredient, get_stock_movement
from ml.features import prepare_sales_features, prepare_ingredient_features, prepare_stock_features
from ml.models import train_model, get_feature_importance, MODEL_REGISTRY

require_login_and_company("ML Insights")

st.title("ML Insights")

# ── choose analysis ───────────────────────────────────────────────────────
analysis = st.sidebar.radio(
    "Analysis type",
    ["Sales Forecasting", "Ingredient Demand", "Stock Demand"],
)
model_name = st.sidebar.selectbox("Model", list(MODEL_REGISTRY.keys()))
test_size = st.sidebar.slider("Test split %", 10, 40, 20) / 100


def _show_results(prefix):
    """Display model results from session_state."""
    if f"{prefix}_model" not in st.session_state:
        st.info("Click **Train Model** to start.")
        return

    metrics = st.session_state[f"{prefix}_metrics"]
    y_test, y_pred = st.session_state[f"{prefix}_test"]
    feat = st.session_state[f"{prefix}_feat"]
    model = st.session_state[f"{prefix}_model"]

    st.subheader("Model Performance")
    m1, m2, m3 = st.columns(3)
    m1.metric("R2 Score", f"{metrics['R2']:.4f}")
    m2.metric("MAE",      f"{metrics['MAE']:,.2f}")
    m3.metric("RMSE",     f"{metrics['RMSE']:,.2f}")

    st.subheader("Actual vs Predicted")
    cmp = pd.DataFrame({"Actual": y_test, "Predicted": y_pred})
    st.line_chart(cmp)
    st.dataframe(cmp.head(30), width="stretch")

    imp = get_feature_importance(model, feat)
    if imp:
        st.subheader("Feature Importance")
        imp_df = pd.DataFrame({"feature": list(imp.keys()), "importance": list(imp.values())})
        imp_df = imp_df.sort_values("importance", ascending=False)
        st.bar_chart(imp_df.set_index("feature"))

    st.subheader("Residual Distribution")
    residuals = y_test - y_pred
    res_df = pd.DataFrame({"residual": residuals})
    st.bar_chart(res_df["residual"].value_counts(bins=20).sort_index())


# ══════════════════════════════════════════════════════════════════════════
#  Sales Forecasting
# ══════════════════════════════════════════════════════════════════════════
if analysis == "Sales Forecasting":
    st.header("Sales Forecasting")
    with st.spinner("Loading sales data..."):
        sales = get_sales_summary()

    if sales.empty:
        st.warning("No sales data. Check DB connection.")
        st.stop()

    X, y, feat = prepare_sales_features(sales)
    if X is None:
        st.warning("Not enough data to build features (need >= 7 days).")
        st.stop()

    st.info(f"Samples: **{len(y)}** | Features: **{', '.join(feat)}**")

    if st.button("Train Model", key="train_sales"):
        model, metrics, y_test, y_pred = train_model(X, y, model_name, test_size)
        st.session_state["sales_model"] = model
        st.session_state["sales_metrics"] = metrics
        st.session_state["sales_test"] = (y_test, y_pred)
        st.session_state["sales_feat"] = feat

    _show_results("sales")

# ══════════════════════════════════════════════════════════════════════════
#  Ingredient Demand
# ══════════════════════════════════════════════════════════════════════════
elif analysis == "Ingredient Demand":
    st.header("Ingredient Demand Prediction")
    with st.spinner("Loading ingredient data..."):
        ingr = get_order_ingredient()

    if ingr.empty:
        st.warning("No ingredient data. Check DB connection.")
        st.stop()

    X, y, feat = prepare_ingredient_features(ingr)
    if X is None:
        st.warning("Not enough ingredient data to build features (need >= 7 days).")
        st.stop()

    st.info(f"Samples: **{len(y)}** | Features: **{', '.join(feat)}**")

    if st.button("Train Model", key="train_ingr"):
        model, metrics, y_test, y_pred = train_model(X, y, model_name, test_size)
        st.session_state["ingr_model"] = model
        st.session_state["ingr_metrics"] = metrics
        st.session_state["ingr_test"] = (y_test, y_pred)
        st.session_state["ingr_feat"] = feat

    _show_results("ingr")

# ══════════════════════════════════════════════════════════════════════════
#  Stock Demand
# ══════════════════════════════════════════════════════════════════════════
else:
    st.header("Stock Demand Prediction")
    st.markdown("Predicts daily stock consumption (stock-out qty) per item using historical movement data.")

    with st.spinner("Loading stock movement data..."):
        stk = get_stock_movement()

    if stk.empty:
        st.warning("No stock movement data. Check DB connection.")
        st.stop()

    X, y, feat = prepare_stock_features(stk)
    if X is None:
        st.warning("Not enough stock data to build features (need >= 7 days of consumption).")
        st.stop()

    st.info(f"Samples: **{len(y)}** | Features: **{', '.join(feat)}**")

    if st.button("Train Model", key="train_stock"):
        model, metrics, y_test, y_pred = train_model(X, y, model_name, test_size)
        st.session_state["stock_model"] = model
        st.session_state["stock_metrics"] = metrics
        st.session_state["stock_test"] = (y_test, y_pred)
        st.session_state["stock_feat"] = feat

    _show_results("stock")
