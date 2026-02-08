"""
Cached data loaders for the Streamlit app.
Each dataset is cached independently (TTL 5 min).
"""
import streamlit as st
from db import load


@st.cache_data(ttl=300)
def get_restaurant_shops():
    return load.load_restaurant_shops()


@st.cache_data(ttl=300)
def get_sales_summary():
    return load.load_sales_summary()


@st.cache_data(ttl=300)
def get_sales_bill_level():
    return load.load_sales_bill_level()


@st.cache_data(ttl=300)
def get_sales_detail():
    return load.load_sales_detail()


@st.cache_data(ttl=300)
def get_service_charge():
    return load.load_service_charge()


@st.cache_data(ttl=300)
def get_order_ingredient():
    return load.load_order_ingredient()


@st.cache_data(ttl=300)
def get_order_header():
    return load.load_order_header()


@st.cache_data(ttl=300)
def get_order_details():
    return load.load_order_details()


@st.cache_data(ttl=300)
def get_payment_mode():
    return load.load_payment_mode()


@st.cache_data(ttl=300)
def get_segment_sales():
    return load.load_segment_sales()


@st.cache_data(ttl=300)
def get_sp_fb_pos_amt():
    return load.load_sp_fb_pos_amt()


@st.cache_data(ttl=300)
def get_currencies():
    return load.load_currencies()


@st.cache_data(ttl=300)
def get_split_payments():
    return load.load_split_payments()


@st.cache_data(ttl=300)
def get_stock_movement():
    return load.load_stock_movement()


@st.cache_data(ttl=300)
def get_customer_profitability():
    return load.load_customer_profitability()


@st.cache_data(ttl=300)
def get_segment_item_pricing():
    return load.load_segment_item_pricing()


@st.cache_data(ttl=300)
def get_sessions():
    return load.load_sessions()


@st.cache_data(ttl=300)
def get_gst_sales():
    return load.load_gst_sales()


@st.cache_data(ttl=300)
def get_denomination_detail():
    return load.load_denomination_detail()


@st.cache_data(ttl=300)
def get_day_end_sales():
    return load.load_day_end_sales()
