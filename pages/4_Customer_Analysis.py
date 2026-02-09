"""
Customer Analysis — Repeat customers, profit/loss, free bill analysis,
segment-wise item pricing.
"""
import streamlit as st
import pandas as pd
from data_loader import get_customer_profitability, get_segment_item_pricing

st.title("Customer Analysis")

# ── load ──────────────────────────────────────────────────────────────────
with st.spinner("Loading customer and pricing data..."):
    try:
        raw = get_customer_profitability()
        seg_price = get_segment_item_pricing()
    except Exception as e:
        st.error(f"Data load error: {e}")
        st.stop()

if raw.empty:
    st.warning("No customer data returned.")
    st.stop()

# ── prep ──────────────────────────────────────────────────────────────────
df = raw.copy()
df["billdate"]  = pd.to_datetime(df["billdate"], errors="coerce")
df["qty"]       = pd.to_numeric(df["qty"], errors="coerce").fillna(0)
df["unitprice"] = pd.to_numeric(df["unitprice"], errors="coerce").fillna(0)
df["costprice"] = pd.to_numeric(df["costprice"], errors="coerce").fillna(0)
df["revenue"]   = df["qty"] * df["unitprice"]
df["cost"]      = df["qty"] * df["costprice"]
df["profit"]    = df["revenue"] - df["cost"]
df["customername"] = df["customername"].fillna("CASH")

# sidebar date filter
if df["billdate"].notna().any():
    mn = df["billdate"].min().date()
    mx = df["billdate"].max().date()
    dr = st.sidebar.date_input("Date range", value=(mn, mx), min_value=mn, max_value=mx, key="cust_dr")
    if len(dr) == 2:
        df = df[(df["billdate"] >= pd.Timestamp(dr[0])) & (df["billdate"] <= pd.Timestamp(dr[1]))]

if df.empty:
    st.warning("No data for selected date range.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
tab_overview, tab_repeat, tab_pnl, tab_free, tab_seg = st.tabs(
    ["Customer Overview", "Repeat Customers", "Profit / Loss",
     "Free Bill Analysis", "Segment Pricing"]
)

# ── TAB 1 – Customer Overview ────────────────────────────────────────────
with tab_overview:
    cust_agg = df.groupby("customername").agg(
        bill_count=("billid", "nunique"),
        total_revenue=("revenue", "sum"),
        total_cost=("cost", "sum"),
        total_profit=("profit", "sum"),
    ).reset_index()

    total_cust = cust_agg.shape[0]
    repeat_cust = (cust_agg["bill_count"] > 1).sum()

    st.subheader("KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Customers", f"{total_cust:,}")
    k2.metric("Repeat Customers", f"{repeat_cust:,}")
    k3.metric("Total Revenue", f"{cust_agg['total_revenue'].sum():,.2f}")
    k4.metric("Total Profit", f"{cust_agg['total_profit'].sum():,.2f}")

    st.subheader("Top 20 Customers by Revenue")
    top20 = cust_agg.nlargest(20, "total_revenue").set_index("customername")
    st.bar_chart(top20["total_revenue"])

    st.subheader("Customer Summary")
    st.dataframe(cust_agg.sort_values("total_revenue", ascending=False).head(50), width="stretch")

# ── TAB 2 – Repeat Customers ─────────────────────────────────────────────
with tab_repeat:
    st.subheader("Repeat Customers (> 1 visit)")
    repeats = cust_agg[cust_agg["bill_count"] > 1].copy()
    if repeats.empty:
        st.info("No repeat customers found.")
    else:
        repeats["avg_spend"] = repeats["total_revenue"] / repeats["bill_count"]
        repeats = repeats.sort_values("bill_count", ascending=False)

        r1, r2, r3 = st.columns(3)
        r1.metric("Repeat Customers", f"{len(repeats):,}")
        r2.metric("Avg Visits", f"{repeats['bill_count'].mean():,.1f}")
        r3.metric("Avg Spend / Visit", f"{repeats['avg_spend'].mean():,.2f}")

        st.subheader("Top Repeat Customers")
        st.bar_chart(repeats.set_index("customername")["bill_count"].head(20))

        st.subheader("Detail")
        st.dataframe(repeats.head(50), width="stretch")

# ── TAB 3 – Profit / Loss ────────────────────────────────────────────────
with tab_pnl:
    st.subheader("Customer Profit / Loss")
    pnl = cust_agg.sort_values("total_profit", ascending=False).copy()

    p1, p2, p3 = st.columns(3)
    p1.metric("Total Revenue", f"{pnl['total_revenue'].sum():,.2f}")
    p2.metric("Total Cost",    f"{pnl['total_cost'].sum():,.2f}")
    p3.metric("Total Profit",  f"{pnl['total_profit'].sum():,.2f}")

    st.subheader("Profit Leaders (Top 15)")
    top_profit = pnl.nlargest(15, "total_profit").set_index("customername")
    st.bar_chart(top_profit["total_profit"])

    loss_cust = pnl[pnl["total_profit"] < 0]
    if not loss_cust.empty:
        st.subheader("Loss Makers")
        st.bar_chart(loss_cust.set_index("customername")["total_profit"])
        st.dataframe(loss_cust, width="stretch")
    else:
        st.info("No loss-making customers.")

    # Free bill customers highlighted
    free_bills = df[df["payment_mode"] == "FREEBILL"]
    if not free_bills.empty:
        st.subheader("Free Bill Customers")
        fb_cust = free_bills.groupby("customername").agg(
            bills=("billid", "nunique"),
            items=("qty", "sum"),
            would_be_revenue=("revenue", "sum"),
            cost_incurred=("cost", "sum"),
        ).reset_index()
        fb_cust["loss"] = fb_cust["cost_incurred"] - fb_cust["would_be_revenue"]
        st.dataframe(fb_cust.sort_values("cost_incurred", ascending=False), width="stretch")

# ── TAB 4 – Free Bill Analysis ───────────────────────────────────────────
with tab_free:
    free = df[df["payment_mode"] == "FREEBILL"].copy()
    if free.empty:
        st.info("No free bills found.")
    else:
        st.subheader("Free Bill Summary")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Free Bills", f"{free['billid'].nunique():,}")
        f2.metric("Items Given", f"{free['qty'].sum():,.0f}")
        f3.metric("Would-Be Revenue (ItemRate)", f"{free['revenue'].sum():,.2f}")
        f4.metric("Cost Incurred", f"{free['cost'].sum():,.2f}")

        st.metric("Net Loss from Free Bills", f"{free['cost'].sum() - free['revenue'].sum():,.2f}")

        st.subheader("Free Bill Items")
        fb_items = free.groupby("itemname").agg(
            qty=("qty", "sum"),
            avg_unitprice=("unitprice", "mean"),
            avg_costprice=("costprice", "mean"),
            total_revenue=("revenue", "sum"),
            total_cost=("cost", "sum"),
        ).reset_index()
        fb_items["loss"] = fb_items["total_cost"] - fb_items["total_revenue"]
        fb_items = fb_items.sort_values("loss", ascending=False)
        st.bar_chart(fb_items.set_index("itemname")["loss"].head(20))
        st.dataframe(fb_items, width="stretch")

        st.subheader("Free Bill Detail")
        st.dataframe(free[["billdate", "billid", "customername", "itemname",
                           "qty", "unitprice", "costprice", "revenue", "cost", "profit"]].head(100),
                     width="stretch")

# ── TAB 5 – Segment Item Pricing (from actual sales) ─────────────────────
with tab_seg:
    if seg_price.empty:
        st.info("No segment pricing data available.")
    else:
        sp = seg_price.copy()
        for c in ["avg_selling_price", "avg_cost_price", "base_rate",
                   "total_qty", "total_revenue", "total_cost"]:
            if c in sp.columns:
                sp[c] = pd.to_numeric(sp[c], errors="coerce").fillna(0)

        # segment filter
        seg_list = sorted(sp["segmentname"].dropna().unique().tolist())
        sel_seg = st.sidebar.selectbox("Segment", ["All"] + seg_list, key="seg_filter")
        if sel_seg != "All":
            sp = sp[sp["segmentname"] == sel_seg]

        st.subheader("Segment-wise Item Pricing (Menu Items)")

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Items", f"{sp['itemid'].nunique():,}")
        s2.metric("Segments", f"{sp['segmentname'].nunique():,}")
        s3.metric("Avg Selling Price", f"{sp['avg_selling_price'].mean():,.2f}")
        s4.metric("Total Revenue", f"{sp['total_revenue'].sum():,.2f}")

        # Revenue and cost per segment
        st.subheader("Revenue and Cost by Segment")
        seg_agg = sp.groupby("segmentname").agg(
            revenue=("total_revenue", "sum"),
            cost=("total_cost", "sum"),
            items_sold=("total_qty", "sum"),
            bills=("bill_count", "sum"),
        ).reset_index()
        seg_agg["profit"] = seg_agg["revenue"] - seg_agg["cost"]
        st.bar_chart(seg_agg.set_index("segmentname")["revenue"])
        st.dataframe(seg_agg.sort_values("revenue", ascending=False), width="stretch")

        # Price comparison: avg selling vs base rate
        st.subheader("Price Comparison: Avg Selling vs Base Rate")
        sp["variance"] = sp["avg_selling_price"] - sp["base_rate"]
        sp["variance_pct"] = ((sp["avg_selling_price"] - sp["base_rate"]) / sp["base_rate"].replace(0, 1)) * 100

        price_cmp = sp[["itemname", "segmentname", "avg_selling_price", "avg_cost_price",
                         "base_rate", "variance", "variance_pct", "total_qty", "total_revenue"]]\
            .sort_values("total_revenue", ascending=False)
        st.dataframe(price_cmp.head(50), width="stretch")

        st.subheader("Top 20 Items by Revenue")
        item_rev = sp.groupby("itemname")["total_revenue"].sum().nlargest(20)
        st.bar_chart(item_rev)

        # Cross-segment price comparison
        if sel_seg == "All" and len(seg_list) > 1:
            st.subheader("Avg Selling Price by Segment (Top 10 Items)")
            top_items = sp.groupby("itemname")["total_revenue"].sum().nlargest(10).index.tolist()
            pivot = sp[sp["itemname"].isin(top_items)].pivot_table(
                index="itemname", columns="segmentname", values="avg_selling_price", aggfunc="mean"
            ).fillna(0)
            st.dataframe(pivot, width="stretch")
