"""
Restaurant Dashboard — Sales (multi-currency), Service Charge, Ingredients,
Split Payments, Segment Analysis.
"""
import streamlit as st
import pandas as pd
from data_loader import (
    get_restaurant_shops,
    get_sales_summary,
    get_sales_bill_level,
    get_service_charge,
    get_order_ingredient,
    get_payment_mode,
    get_segment_sales,
    get_currencies,
    get_split_payments,
    get_sessions,
)

st.title("Restaurant Dashboard")

# ── load data ──────────────────────────────────────────────────────────────
with st.spinner("Loading data from database..."):
    try:
        shops      = get_restaurant_shops()
        sales      = get_sales_summary()
        sales_bill = get_sales_bill_level()
        svc        = get_service_charge()
        ingr       = get_order_ingredient()
        pay        = get_payment_mode()
        seg        = get_segment_sales()
        currencies = get_currencies()
        split_pay  = get_split_payments()
        sessions   = get_sessions()
    except Exception as e:
        st.error(f"Data load error: {e}")
        st.stop()

if sales.empty:
    st.warning("No sales data returned. Verify DB connection and table access.")
    st.stop()

# ── sidebar filters ───────────────────────────────────────────────────────
st.sidebar.header("Filters")

shop_options = ["All"] + (shops["ShopName"].dropna().unique().tolist() if not shops.empty else [])
selected_shop = st.sidebar.selectbox("Shop", shop_options)

# Session filter (for cross-midnight reporting)
session_mode = False
if not sessions.empty:
    sessions["open_time"]  = pd.to_datetime(sessions["open_time"])
    sessions["close_time"] = pd.to_datetime(sessions["close_time"])
    sessions["label"] = (
        sessions["session_no"] + " | " +
        sessions["open_time"].dt.strftime("%d-%b %H:%M") + " - " +
        sessions["close_time"].dt.strftime("%d-%b %H:%M") + " | " +
        sessions["counter_name"]
    )
    sess_opts = ["Date filter (default)"] + sessions["label"].tolist()
    sel_sess = st.sidebar.selectbox("Session", sess_opts, key="dash_session")
    if sel_sess != "Date filter (default)":
        session_mode = True
        sess_row = sessions[sessions["label"] == sel_sess].iloc[0]
        start_b = int(sess_row["start_bill"])
        end_b   = int(sess_row["end_bill"])
        tid     = int(sess_row["tillid"])
        # Filter bill-level data by session
        sales_bill["billdate"] = pd.to_datetime(sales_bill["billdate"])
        sb = sales_bill[
            (sales_bill["billid"] > start_b) &
            (sales_bill["billid"] <= end_b) &
            (sales_bill["counterid"] == tid)
        ]
        # Re-aggregate to match sales summary shape
        if not sb.empty:
            sales = sb.groupby(["shopid", "shopname", "billdate"]).agg(
                total_bills=("billid", "count"),
                total_amount=("total_amount", "sum"),
                total_damount=("total_damount", "sum"),
                total_camount=("total_camount", "sum"),
                total_discount=("total_discount", "sum"),
                total_service_charge=("total_service_charge", "sum"),
                avg_bill_value=("total_amount", "mean"),
                total_cash=("total_cash", "sum"),
                total_card=("total_card", "sum"),
                total_credit=("total_credit", "sum"),
            ).reset_index()
        else:
            sales = pd.DataFrame()

if sales.empty:
    st.warning("No sales data for selected session.")
    st.stop()
sales["billdate"] = pd.to_datetime(sales["billdate"])

sales["billdate"] = pd.to_datetime(sales["billdate"])
min_date = sales["billdate"].min().date()
max_date = sales["billdate"].max().date()

if "dr" not in st.session_state:
    st.session_state.dr = (min_date, max_date)

date_range = st.sidebar.date_input(
    "Date Range",
    key="dr",
    min_value=min_date,
    max_value=max_date
)


# Currency toggle
cur_options = {"Base": "total_amount"}
if "total_damount" in sales.columns:
    cur_options["Department"] = "total_damount"
if "total_camount" in sales.columns:
    cur_options["Company"] = "total_camount"
cur_label = st.sidebar.radio("Currency view", list(cur_options.keys()))
amt_col = cur_options[cur_label]

# Build currency symbol map
cur_symbol = ""
if not currencies.empty:
    sym_map = dict(zip(currencies["CurrencyName"], currencies["Symbol"]))
    if cur_label == "Base":
        cur_symbol = list(sym_map.values())[0] if sym_map else ""
    elif cur_label == "Department" and len(sym_map) > 1:
        cur_symbol = list(sym_map.values())[1] if len(sym_map) > 1 else ""
    elif cur_label == "Company" and len(sym_map) > 0:
        cur_symbol = list(sym_map.values())[-1] if sym_map else ""

# apply filters
if selected_shop != "All" and not shops.empty:
    shop_id = shops.loc[shops["ShopName"] == selected_shop, "ShopID"].iloc[0]
    sales = sales[sales["shopid"] == shop_id]
    if not svc.empty and "shopid" in svc.columns:
        svc = svc[svc["shopid"] == shop_id]
    if not ingr.empty and "shopid" in ingr.columns:
        ingr = ingr[ingr["shopid"] == shop_id]
    if not pay.empty and "shopid" in pay.columns:
        pay = pay[pay["shopid"] == shop_id]
    if not seg.empty and "shopid" in seg.columns:
        seg = seg[seg["shopid"] == shop_id]
    if not split_pay.empty and "shopid" in split_pay.columns:
        split_pay = split_pay[split_pay["shopid"] == shop_id]

if len(date_range) == 2:
    d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    sales = sales[(sales["billdate"] >= d0) & (sales["billdate"] <= d1)]

if sales.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════
tab_sales, tab_svc, tab_ingr, tab_pay, tab_seg, tab_data = st.tabs(
    ["Sales Overview", "Service Charge", "Ingredient Consumption",
     "Split Payments", "Segment Analysis", "Raw Data"]
)

# ── TAB 1 – Sales overview (multi-currency) ──────────────────────────────
with tab_sales:
    st.subheader(f"Key Metrics ({cur_symbol})" if cur_symbol else "Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue",   f"{cur_symbol} {sales[amt_col].sum():,.0f}")
    c2.metric("Total Bills",     f"{sales['total_bills'].sum():,.0f}")
    c3.metric("Avg Bill Value",  f"{cur_symbol} {sales[amt_col].mean():,.2f}")
    c4.metric("Total Discount",  f"{cur_symbol} {sales['total_discount'].sum():,.0f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Cash Sales",   f"{cur_symbol} {sales['total_cash'].sum():,.0f}")
    c6.metric("Card Sales",   f"{cur_symbol} {sales['total_card'].sum():,.0f}")
    c7.metric("Credit Sales", f"{cur_symbol} {sales['total_credit'].sum():,.0f}")

    st.subheader("Daily Revenue Trend")
    daily = sales.groupby("billdate")[amt_col].sum().reset_index()
    daily = daily.set_index("billdate").sort_index()
    st.line_chart(daily)

    st.subheader("Revenue by Shop")
    by_shop = sales.groupby("shopname")[amt_col].sum().sort_values(ascending=False)
    st.bar_chart(by_shop)

    st.subheader("Bills per Day")
    bills_day = sales.groupby("billdate")["total_bills"].sum().reset_index().set_index("billdate").sort_index()
    st.area_chart(bills_day)

# ── TAB 2 – Service charge ───────────────────────────────────────────────
with tab_svc:
    if svc.empty:
        st.info("No service-charge data available.")
    else:
        st.subheader("Service Charge Summary")
        svc["billdate"] = pd.to_datetime(svc["billdate"])
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Total Service Charge", f"{svc['amount'].sum():,.2f}")
        sc2.metric("Tax Amount",           f"{svc['TaxAmount'].sum():,.2f}")
        sc3.metric("Avg Tax %",            f"{svc['TaxPercentage'].mean():,.2f}%")

        st.subheader("Service Charge Trend")
        svc_daily = svc.groupby("billdate")["amount"].sum().reset_index().set_index("billdate").sort_index()
        st.line_chart(svc_daily)

        st.subheader("By Customer")
        cust = svc.groupby("poshCustomerName")["amount"].sum().nlargest(15)
        st.bar_chart(cust)

# ── TAB 3 – Ingredient consumption ───────────────────────────────────────
with tab_ingr:
    if ingr.empty:
        st.info("No ingredient consumption data available.")
    else:
        st.subheader("Ingredient Consumption Overview")
        ingr["sdate"] = pd.to_datetime(ingr["sdate"])
        i1, i2, i3 = st.columns(3)
        i1.metric("Total Qty Consumed",  f"{ingr['cashsales'].sum():,.2f}")
        i2.metric("Avg Cost Price",      f"{ingr['costprice'].mean():,.2f}")
        i3.metric("Total Cost Value",    f"{(ingr['cashsales'] * ingr['costprice']).sum():,.2f}")

        st.subheader("Daily Ingredient Usage")
        ingr_daily = ingr.groupby("sdate")["cashsales"].sum().reset_index().set_index("sdate").sort_index()
        st.line_chart(ingr_daily)

        st.subheader("Top 15 Ingredients by Qty")
        if "packingtype" in ingr.columns:
            ingr["_label"] = ingr["itemname"] + " (" + ingr["packingtype"].fillna("") + ")"
            top_items = ingr.groupby("_label")["cashsales"].sum().nlargest(15)
        else:
            top_items = ingr.groupby("itemname")["cashsales"].sum().nlargest(15)
        st.bar_chart(top_items)

        st.subheader("Cost Analysis: Cost vs Consumption")
        grp_cols = ["itemname"]
        if "packingtype" in ingr.columns:
            grp_cols.append("packingtype")
        cost_df = ingr.groupby(grp_cols).agg(
            total_qty=("cashsales", "sum"),
            avg_cost=("costprice", "mean"),
        ).reset_index()
        cost_df["total_cost"] = cost_df["total_qty"] * cost_df["avg_cost"]
        st.dataframe(cost_df.nlargest(20, "total_cost"), width="stretch")

# ── TAB 4 – Split Payments ───────────────────────────────────────────────
with tab_pay:
    # Header-level payment mode summary (existing)
    if pay.empty and split_pay.empty:
        st.info("No payment data available.")
    else:
        # Overall payment mode from header
        st.subheader("Payment Mode Summary (Header)")
        if not pay.empty:
            pm = pay.groupby("payment_mode").agg(
                total_amount=("amount", "sum"),
                total_bills=("bill_count", "sum"),
            ).sort_values("total_amount", ascending=False)
            st.bar_chart(pm["total_amount"])
            st.dataframe(pm.reset_index(), width="stretch")

        # Split payment detail
        st.subheader("Split Payment Breakdown")
        if split_pay.empty:
            st.info("No split payment detail data.")
        else:
            split_pay["billdate"] = pd.to_datetime(split_pay["billdate"])
            if len(date_range) == 2:
                split_pay = split_pay[
                    (split_pay["billdate"] >= d0) & (split_pay["billdate"] <= d1)
                ]

            sp1, sp2, sp3 = st.columns(3)
            sp1.metric("Total Split Bills", f"{split_pay['billid'].nunique():,}")
            sp2.metric("Total Split Amount", f"{split_pay['amount'].sum():,.2f}")
            sp3.metric("Avg Split per Bill", f"{split_pay.groupby('billid')['amount'].sum().mean():,.2f}")

            st.subheader("By Payment Type")
            by_type = split_pay.groupby("payment_type")["amount"].sum().sort_values(ascending=False)
            st.bar_chart(by_type)

            st.subheader("By Account")
            by_acc = split_pay.groupby("account_name")["amount"].sum().sort_values(ascending=False)
            st.bar_chart(by_acc)

            st.subheader("Split vs Single-Mode Bills")
            header_modes = pay.groupby("payment_mode")["bill_count"].sum() if not pay.empty else pd.Series(dtype=float)
            if not header_modes.empty:
                st.dataframe(header_modes.reset_index(), width="stretch")

            st.subheader("Split Payment Detail")
            st.dataframe(split_pay.head(100), width="stretch")

# ── TAB 5 – Segment analysis ─────────────────────────────────────────────
with tab_seg:
    if seg.empty:
        st.info("No segment data available.")
    else:
        st.subheader("Revenue by Segment")
        seg_total = seg.groupby("segmentname").agg(
            total_amount=("amount", "sum"),
            total_bills=("bill_count", "sum"),
        ).sort_values("total_amount", ascending=False)
        st.bar_chart(seg_total["total_amount"])

        st.subheader("Segment Detail")
        st.dataframe(seg_total.reset_index(), width="stretch")

        st.subheader("Segment Trend Over Time")
        seg["billdate"] = pd.to_datetime(seg["billdate"])
        seg_time = seg.groupby(["billdate", "segmentname"])["amount"].sum().unstack(fill_value=0)
        st.line_chart(seg_time)

# ── TAB 6 – Raw data preview ─────────────────────────────────────────────
with tab_data:
    st.subheader("Sales Summary")
    st.dataframe(sales.head(100), width="stretch")
    st.subheader("Service Charge")
    st.dataframe(svc.head(100), width="stretch")
    st.subheader("Ingredient Report")
    st.dataframe(ingr.head(100), width="stretch")
    st.subheader("Split Payments")
    st.dataframe(split_pay.head(100), width="stretch")
    st.subheader("Segment Sales")
    st.dataframe(seg.head(100), width="stretch")
