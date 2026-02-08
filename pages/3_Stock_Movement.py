"""
Stock Movement Dashboard — Full inventory flow across 20+ transaction types.
mode=1 stock IN, mode=-1 stock OUT.
"""
import streamlit as st
import pandas as pd
from data_loader import get_stock_movement, get_restaurant_shops, get_currencies

st.title("Stock Movement")

# ── load ──────────────────────────────────────────────────────────────────
with st.spinner("Loading stock movement data..."):
    try:
        stk_raw = get_stock_movement()
        shops   = get_restaurant_shops()
        currencies = get_currencies()
    except Exception as e:
        st.error(f"Data load error: {e}")
        st.stop()

if stk_raw.empty:
    st.warning("No stock movement data returned.")
    st.stop()

# work on a copy so cached data stays clean
stk = stk_raw.copy()
stk["sdate"] = pd.to_datetime(stk["sdate"], errors="coerce")
stk["qty"]   = pd.to_numeric(stk["qty"], errors="coerce").fillna(0)
stk["mode"]  = pd.to_numeric(stk["mode"], errors="coerce").fillna(0).astype(int)
for c in ["costprice", "depcostprice", "concostprice"]:
    if c in stk.columns:
        stk[c] = pd.to_numeric(stk[c], errors="coerce").fillna(0)

# pre-compute cost columns for all three currencies
stk["cost_base"] = stk["qty"] * stk["costprice"]
stk["cost_dept"] = stk["qty"] * stk["depcostprice"]
stk["cost_comp"] = stk["qty"] * stk["concostprice"]

# ── sidebar filters ──────────────────────────────────────────────────────
st.sidebar.header("Stock Filters")

# shop
shop_options = ["All"] + (shops["ShopName"].dropna().unique().tolist() if not shops.empty else [])
sel_shop = st.sidebar.selectbox("Shop", shop_options, key="stk_shop")
if sel_shop != "All" and not shops.empty:
    sid = shops.loc[shops["ShopName"] == sel_shop, "ShopID"].iloc[0]
    stk = stk[stk["shopid"] == sid]

# ---- Initialize date range once ----
if "stk_dr" not in st.session_state:
    if stk["sdate"].notna().any():
        st.session_state.stk_dr = (
            stk["sdate"].min().date(),
            stk["sdate"].max().date()
        )

# ---- Sidebar input (controlled by session_state) ----
dr = st.sidebar.date_input(
    "Date range",
    value=st.session_state.stk_dr,
    key="stk_dr"
)

# ---- Apply filter only when user selects ----
if len(dr) == 2:
    stk = stk[
        (stk["sdate"] >= pd.Timestamp(dr[0])) &
        (stk["sdate"] <= pd.Timestamp(dr[1]))
    ]

# type filter
all_types = sorted(stk["type"].dropna().unique().tolist())
sel_types = st.sidebar.multiselect("Transaction types", all_types, default=all_types, key="stk_types")
if sel_types:
    stk = stk[stk["type"].isin(sel_types)]

if stk.empty:
    st.warning("No data for selected filters.")
    st.stop()

# currency selector
cur_options = {"Base": "cost_base", "Department": "cost_dept", "Company": "cost_comp"}
cur_label = st.sidebar.radio("Cost currency", list(cur_options.keys()), key="stk_cur")
cost_col = cur_options[cur_label]

# currency symbol
cur_symbol = ""
if not currencies.empty:
    sym_list = currencies["Symbol"].tolist()
    if cur_label == "Base" and len(sym_list) > 0:
        cur_symbol = sym_list[0]
    elif cur_label == "Department" and len(sym_list) > 1:
        cur_symbol = sym_list[1]
    elif cur_label == "Company" and len(sym_list) > 0:
        cur_symbol = sym_list[-1]

# derived
stk_in  = stk[stk["mode"] == 1]
stk_out = stk[stk["mode"] == -1]

# ══════════════════════════════════════════════════════════════════════════
tab_overview, tab_type, tab_item, tab_cost, tab_raw = st.tabs(
    ["Stock Overview", "By Transaction Type", "By Item", "Cost Analysis", "Raw Data"]
)

# ── TAB 1 – Overview ─────────────────────────────────────────────────────
with tab_overview:
    st.subheader("KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Stock In",  f"{stk_in['qty'].sum():,.2f}")
    k2.metric("Total Stock Out", f"{stk_out['qty'].sum():,.2f}")
    k3.metric("Net Movement",    f"{stk_in['qty'].sum() - stk_out['qty'].sum():,.2f}")
    k4.metric(f"Total Cost ({cur_symbol})", f"{cur_symbol} {stk[cost_col].sum():,.2f}")

    st.subheader("Daily Stock In vs Out")
    daily_in  = stk_in.groupby("sdate")["qty"].sum().rename("Stock In")
    daily_out = stk_out.groupby("sdate")["qty"].sum().rename("Stock Out")
    daily_df  = pd.concat([daily_in, daily_out], axis=1).fillna(0).sort_index()
    st.line_chart(daily_df)

    st.subheader("Cumulative Net Stock")
    daily_df["Net"] = daily_df.get("Stock In", 0) - daily_df.get("Stock Out", 0)
    daily_df["Cumulative"] = daily_df["Net"].cumsum()
    st.area_chart(daily_df["Cumulative"])

# ── TAB 2 – By Transaction Type ──────────────────────────────────────────
with tab_type:
    st.subheader("Quantity by Transaction Type")
    by_type = stk.groupby("type").agg(
        total_qty=("qty", "sum"),
        transaction_count=("transid", "count"),
    ).sort_values("total_qty", ascending=False)
    st.bar_chart(by_type["total_qty"])

    st.subheader("Detail")
    st.dataframe(by_type.reset_index(), width="stretch")

    st.subheader("Stock In Types")
    if not stk_in.empty:
        in_types = stk_in.groupby("type")["qty"].sum().sort_values(ascending=False)
        st.bar_chart(in_types)
    else:
        st.info("No stock-in records.")

    st.subheader("Stock Out Types")
    if not stk_out.empty:
        out_types = stk_out.groupby("type")["qty"].sum().sort_values(ascending=False)
        st.bar_chart(out_types)
    else:
        st.info("No stock-out records.")

# ── TAB 3 – By Item ──────────────────────────────────────────────────────
with tab_item:
    has_name = "itemname" in stk.columns
    item_grp = "itemname" if has_name else "itemid"

    st.subheader("Top 20 Items by Movement Volume")
    by_item = stk.groupby(item_grp)["qty"].sum().nlargest(20)
    st.bar_chart(by_item)

    st.subheader("Per-Item In/Out Breakdown (Top 20)")
    grp_cols = [item_grp]
    if "packingtype" in stk.columns:
        grp_cols.append("packingtype")

    in_agg  = stk_in.groupby(grp_cols)["qty"].sum().rename("stock_in")
    out_agg = stk_out.groupby(grp_cols)["qty"].sum().rename("stock_out")
    item_io = pd.concat([in_agg, out_agg], axis=1).fillna(0)
    item_io["net"] = item_io["stock_in"] - item_io["stock_out"]
    item_io = item_io.sort_values("stock_out", ascending=False).head(20)
    st.dataframe(item_io.reset_index(), width="stretch")

# ── TAB 4 – Cost Analysis ────────────────────────────────────────────────
with tab_cost:
    st.subheader(f"Cost by Transaction Type ({cur_label} {cur_symbol})")
    cost_by_type = stk.groupby("type")[cost_col].sum().sort_values(ascending=False)
    st.bar_chart(cost_by_type)

    st.subheader("Cost Comparison (Base vs Dept vs Company)")
    cost_cmp = stk.groupby("type").agg(
        base_cost=("cost_base", "sum"),
        dept_cost=("cost_dept", "sum"),
        comp_cost=("cost_comp", "sum"),
    ).sort_values("base_cost", ascending=False)
    st.dataframe(cost_cmp.reset_index(), width="stretch")

    st.subheader(f"Top 20 Items by Cost ({cur_label} {cur_symbol})")
    cost_grp = "itemname" if "itemname" in stk.columns else "itemid"
    item_cost = stk.groupby(cost_grp)[cost_col].sum().nlargest(20)
    st.bar_chart(item_cost)

# ── TAB 5 – Raw Data ─────────────────────────────────────────────────────
with tab_raw:
    st.subheader(f"Stock Movement ({len(stk):,} rows)")
    display_cols = [c for c in ["shopid", "itemname", "packingtype", "sdate", "transno",
                                 "qty", "type", "mode", "costprice", "depcostprice",
                                 "concostprice", "from_to"] if c in stk.columns]
    st.dataframe(stk[display_cols].head(200), width="stretch")
