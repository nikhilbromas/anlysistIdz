"""
Operations — Sessions, GST Sales, Denomination, Day End Sales & Summary.
Supports session-based (cross-midnight) reporting.
"""
import streamlit as st
import pandas as pd
import numpy as np
from data_loader import (
    get_sessions,
    get_gst_sales,
    get_denomination_detail,
    get_day_end_sales,
)

st.title("Operations")

# ── load ──────────────────────────────────────────────────────────────────
with st.spinner("Loading operations data..."):
    try:
        sessions = get_sessions()
        gst      = get_gst_sales()
        deno     = get_denomination_detail()
        dayend   = get_day_end_sales()
    except Exception as e:
        st.error(f"Data load error: {e}")
        st.stop()

# ── prep sessions ─────────────────────────────────────────────────────────
if not sessions.empty:
    sessions["open_time"]  = pd.to_datetime(sessions["open_time"])
    sessions["close_time"] = pd.to_datetime(sessions["close_time"])
    sessions["duration_min"] = (sessions["close_time"] - sessions["open_time"]).dt.total_seconds() / 60
    sessions["duration"] = sessions["duration_min"].apply(
        lambda m: f"{int(abs(m)//60)} hrs {int(abs(m)%60)} min" if pd.notna(m) else ""
    )
    sessions["cross_midnight"] = sessions["open_time"].dt.date != sessions["close_time"].dt.date
    sessions["label"] = (
        sessions["session_no"] + " | " +
        sessions["open_time"].dt.strftime("%d-%b %H:%M") + " - " +
        sessions["close_time"].dt.strftime("%d-%b %H:%M") + " | " +
        sessions["counter_name"]
    )

# ── prep numeric columns ─────────────────────────────────────────────────
for df in [gst, deno, dayend]:
    if not df.empty:
        for c in df.select_dtypes(include=["object"]).columns:
            try:
                df[c] = pd.to_numeric(df[c], errors="ignore")
            except Exception:
                pass

if not dayend.empty:
    for c in ["cash_amount", "card_amount", "bank_amount", "credit_amount",
              "bill_amount", "tax_amount", "amount_without_tax", "return_amount", "service_charge"]:
        if c in dayend.columns:
            dayend[c] = pd.to_numeric(dayend[c], errors="coerce").fillna(0)
    dayend["billdate"] = pd.to_datetime(dayend["billdate"], errors="coerce")

if not gst.empty:
    gst["billdate"] = pd.to_datetime(gst["billdate"], errors="coerce")
    for c in ["amount", "damount", "camount", "GSTAmount", "dGSTAmount", "cGSTAmount"]:
        if c in gst.columns:
            gst[c] = pd.to_numeric(gst[c], errors="coerce").fillna(0)

# ── sidebar: session selector ─────────────────────────────────────────────
st.sidebar.header("Operations Filters")

session_opts = ["All (date filter)"]
if not sessions.empty:
    session_opts += sessions["label"].tolist()
sel_session = st.sidebar.selectbox("Session", session_opts, key="ops_session")

# date filter (used when no specific session selected)
if not dayend.empty and dayend["billdate"].notna().any():
    mn = dayend["billdate"].min().date()
    mx = dayend["billdate"].max().date()
    date_range = st.sidebar.date_input("Date range", value=(mn, mx), min_value=mn, max_value=mx, key="ops_dr")
else:
    date_range = ()


def filter_by_session(df, date_col="billdate", billid_col="billid", counter_col=None):
    """Filter a DataFrame by session bill range or date range."""
    if sel_session != "All (date filter)" and not sessions.empty:
        row = sessions[sessions["label"] == sel_session].iloc[0]
        start_b, end_b, tid = int(row["start_bill"]), int(row["end_bill"]), int(row["tillid"])
        if billid_col in df.columns:
            mask = (df[billid_col] > start_b) & (df[billid_col] <= end_b)
            if counter_col and counter_col in df.columns:
                mask = mask & (df[counter_col] == tid)
            return df[mask]
    # fallback: date filter
    if len(date_range) == 2 and date_col in df.columns:
        d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        return df[(df[date_col] >= d0) & (df[date_col] <= d1)]
    return df


# ══════════════════════════════════════════════════════════════════════════
tab_sess, tab_gst, tab_deno, tab_de_sales, tab_de_summary = st.tabs(
    ["Session Overview", "GST Sales", "Denomination", "Day End Sales", "Day End Summary"]
)

# ── TAB 1 – Session Overview ─────────────────────────────────────────────
with tab_sess:
    if sessions.empty:
        st.info("No session data available.")
    else:
        st.subheader("Till Sessions")
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Sessions", f"{len(sessions):,}")
        k2.metric("Cross-Midnight", f"{sessions['cross_midnight'].sum():,}")
        k3.metric("Avg Duration", f"{sessions['duration_min'].mean():,.0f} min")

        st.subheader("Session List")
        display = sessions[["session_no", "open_time", "close_time", "duration",
                            "counter_name", "user_name", "cross_midnight",
                            "start_bill", "end_bill"]].copy()
        display["open_time"] = display["open_time"].dt.strftime("%d-%b-%Y %H:%M")
        display["close_time"] = display["close_time"].dt.strftime("%d-%b-%Y %H:%M")
        st.dataframe(display.head(100), width="stretch")

        st.subheader("Sessions by Counter")
        by_counter = sessions.groupby("counter_name").agg(
            session_count=("session_id", "count"),
            avg_duration=("duration_min", "mean"),
        ).sort_values("session_count", ascending=False)
        st.bar_chart(by_counter["session_count"])

# ── TAB 2 – GST Sales ────────────────────────────────────────────────────
with tab_gst:
    if gst.empty:
        st.info("No GST sales data available.")
    else:
        gf = gst.copy()
        if len(date_range) == 2:
            d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            gf = gf[(gf["billdate"] >= d0) & (gf["billdate"] <= d1)]

        if gf.empty:
            st.warning("No GST data for selected dates.")
        else:
            st.subheader("GST Sales Summary")
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Net Sales", f"{gf['amount'].sum():,.2f}")
            g2.metric("GST Amount", f"{gf['GSTAmount'].sum():,.2f}")
            g3.metric("Total (incl GST)", f"{(gf['amount'] + gf['GSTAmount']).sum():,.2f}")
            g4.metric("Dept Currency", f"{gf['damount'].sum():,.2f}")

            st.subheader("Cash vs Credit Split")
            cash_credit = gf.groupby("cash").agg(
                net_amount=("amount", "sum"),
                gst=("GSTAmount", "sum"),
            ).reset_index()
            cash_credit["cash"] = cash_credit["cash"].map({1: "Cash", 0: "Credit"})
            st.dataframe(cash_credit, width="stretch")

            st.subheader("Daily GST Trend")
            daily_gst = gf.groupby("billdate").agg(
                net_amount=("amount", "sum"),
                gst_amount=("GSTAmount", "sum"),
            ).sort_index()
            st.line_chart(daily_gst)

            st.subheader("By Transaction Type")
            by_trans = gf.groupby("transtype").agg(
                net_amount=("amount", "sum"),
                gst_amount=("GSTAmount", "sum"),
            ).sort_values("net_amount", ascending=False)
            st.dataframe(by_trans.reset_index(), width="stretch")

            st.subheader("GST Detail")
            st.dataframe(gf.head(100), width="stretch")

# ── TAB 3 – Denomination ─────────────────────────────────────────────────
with tab_deno:
    if deno.empty:
        st.info("No denomination data available.")
    else:
        # session selector for denomination
        if not sessions.empty and sel_session != "All (date filter)":
            row = sessions[sessions["label"] == sel_session].iloc[0]
            sid = int(row["close_id"])  # denomination detail is on the close record
            dd = deno[deno["session_id"] == sid]
            if dd.empty:
                # try the open id
                dd = deno[deno["session_id"] == int(row["session_id"])]
            st.subheader(f"Denomination: {sel_session}")
        else:
            dd = deno.copy()
            st.subheader("Denomination Summary (All Sessions)")

        if dd.empty:
            st.info("No denomination data for selected session.")
        else:
            for c in ["denomination", "deno_count", "amount", "dep_amount"]:
                if c in dd.columns:
                    dd[c] = pd.to_numeric(dd[c], errors="coerce").fillna(0)

            st.subheader("Total by Currency")
            by_cur = dd.groupby(["currencyname", "symbol"]).agg(
                total_amount=("amount", "sum"),
                total_dep=("dep_amount", "sum"),
            ).reset_index()
            st.dataframe(by_cur, width="stretch")

            st.subheader("Denomination Breakdown")
            dd_display = dd[dd["deno_count"] > 0].copy()
            if not dd_display.empty:
                st.dataframe(
                    dd_display[["session_id", "currencyname", "denomination", "deno_count", "amount"]]\
                        .sort_values(["session_id", "currencyname", "denomination"], ascending=[False, True, False]),
                    width="stretch"
                )
            else:
                st.dataframe(dd.head(50), width="stretch")

# ── TAB 4 – Day End Sales ────────────────────────────────────────────────
with tab_de_sales:
    if dayend.empty:
        st.info("No day-end sales data available.")
    else:
        de = filter_by_session(dayend, billid_col="billid", counter_col="counterid")

        if de.empty:
            st.warning("No data for selected filter.")
        else:
            st.subheader("Day End Sales (Bill Level)")
            k1, k2, k3, k4 = st.columns(4)
            sales_only = de[de["view_order"] == 1]
            returns_only = de[de["view_order"] == 2]
            k1.metric("Sales Bills", f"{len(sales_only):,}")
            k2.metric("Return Bills", f"{len(returns_only):,}")
            k3.metric("Net Sales", f"{de['bill_amount'].sum():,.2f}")
            k4.metric("Service Charges", f"{de['service_charge'].sum():,.2f}")

            st.subheader("Payment Split")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Cash", f"{de['cash_amount'].sum():,.2f}")
            p2.metric("Card", f"{de['card_amount'].sum():,.2f}")
            p3.metric("Bank", f"{de['bank_amount'].sum():,.2f}")
            p4.metric("Credit", f"{de['credit_amount'].sum():,.2f}")

            t1, t2 = st.columns(2)
            t1.metric("Tax Amount", f"{de['tax_amount'].sum():,.2f}")
            t2.metric("Amount Without Tax", f"{de['amount_without_tax'].sum():,.2f}")

            st.subheader("Bill Detail")
            show_cols = ["billdate", "billno", "billtime", "cash_amount", "card_amount",
                         "bank_amount", "credit_amount", "bill_amount", "tax_amount",
                         "amount_without_tax", "service_charge", "return_amount", "view_order"]
            show_cols = [c for c in show_cols if c in de.columns]
            st.dataframe(de[show_cols].sort_values(["billdate", "billno"]).head(200), width="stretch")

# ── TAB 5 – Day End Summary ──────────────────────────────────────────────
with tab_de_summary:
    if dayend.empty:
        st.info("No day-end data available.")
    else:
        de = filter_by_session(dayend, billid_col="billid", counter_col="counterid")

        if de.empty:
            st.warning("No data for selected filter.")
        else:
            st.subheader("Day End Summary")

            # Group by date
            summary = de.groupby("billdate").agg(
                bills=("billid", "count"),
                cash=("cash_amount", "sum"),
                card=("card_amount", "sum"),
                bank=("bank_amount", "sum"),
                credit=("credit_amount", "sum"),
                total_sales=("bill_amount", "sum"),
                tax=("tax_amount", "sum"),
                net_without_tax=("amount_without_tax", "sum"),
                service_charges=("service_charge", "sum"),
                returns=("return_amount", "sum"),
            ).sort_index(ascending=False)
            summary["net_sales"] = summary["total_sales"] - summary["returns"].abs()

            st.dataframe(summary.reset_index(), width="stretch")

            st.subheader("Daily Net Sales Trend")
            st.line_chart(summary["net_sales"].sort_index())

            st.subheader("Payment Mode Trend")
            pay_trend = summary[["cash", "card", "bank", "credit"]].sort_index()
            st.line_chart(pay_trend)

            st.subheader("Tax & Service Charge Trend")
            tax_trend = summary[["tax", "service_charges"]].sort_index()
            st.line_chart(tax_trend)

            # Grand total
            st.subheader("Grand Total")
            gt = pd.DataFrame({
                "Metric": ["Total Bills", "Cash", "Card", "Bank", "Credit",
                           "Gross Sales", "Returns", "Net Sales",
                           "Tax", "Net Without Tax", "Service Charges"],
                "Amount": [
                    f"{summary['bills'].sum():,.0f}",
                    f"{summary['cash'].sum():,.2f}",
                    f"{summary['card'].sum():,.2f}",
                    f"{summary['bank'].sum():,.2f}",
                    f"{summary['credit'].sum():,.2f}",
                    f"{summary['total_sales'].sum():,.2f}",
                    f"{summary['returns'].sum():,.2f}",
                    f"{summary['net_sales'].sum():,.2f}",
                    f"{summary['tax'].sum():,.2f}",
                    f"{summary['net_without_tax'].sum():,.2f}",
                    f"{summary['service_charges'].sum():,.2f}",
                ],
            })
            st.dataframe(gt, width="stretch")
