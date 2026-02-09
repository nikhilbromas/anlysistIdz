"""
Streamlit UI helpers for authentication and company selection.

- `render_login_form`     – email/password login against Auth DB
- `render_company_selector` – choose company and set active POS DB
- `require_login_and_company` – guard pages before DB usage
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from auth.service import auth_service
from config import set_active_company_connection, clear_active_company_connection


def render_login_form() -> None:
    """Render login form and authenticate user."""
    st.subheader("Login")
    with st.form("auth_login_form", clear_on_submit=False):
        email = st.text_input("Email", key="auth_email")
        password = st.text_input("Password", type="password", key="auth_password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
                return
            user = auth_service.authenticate_user(email, password)
            if not user:
                st.error("Invalid email or password.")
                return

            st.session_state["auth_user"] = user
            # Load companies for this user
            companies = auth_service.get_user_companies(user["user_id"])
            st.session_state["available_companies"] = companies
            st.success("Login successful. Please select a company.")


def render_company_selector() -> None:
    """Render company selector for the logged-in user and set active DB."""
    user: Dict[str, Any] = st.session_state.get("auth_user") or {}
    companies: List[Dict[str, Any]] = st.session_state.get("available_companies") or []

    st.subheader("Select Company")
    if not companies:
        st.info("No companies mapped to this user.")
        return

    # Build labels
    labels = [
        f"{row.get('CompanyName', 'Company')} (ID {row.get('CompanyId', row.get('CompanyID', '') )})"
        for row in companies
    ]

    idx = st.selectbox("Company", list(range(len(labels))), format_func=lambda i: labels[i])
    if st.button("Use this company"):
        row = companies[idx]
        # CompanyID key may be CompanyId or CompanyID
        company_id = row.get("CompanyId") or row.get("CompanyID")
        details = auth_service.get_company_details(int(company_id))
        if not details:
            st.error("Could not load company connection details.")
            return

        server = details.get("DBserver", "")
        database = details.get("DBname", "")
        user_name = details.get("DBuserName", "")
        password = details.get("DBpassword", "")

        set_active_company_connection(
            server=server,
            database=database,
            user=user_name,
            password=password,
        )

        st.session_state["active_company"] = details
        st.success(f"Active company set to {details.get('CompanyName', 'selected company')}.")
        # Re-run app with new active DB (Streamlit >= 1.27 uses st.rerun)
        st.rerun()


def _render_auth_sidebar() -> None:
    """Small sidebar section showing current user/company and logout."""
    user = st.session_state.get("auth_user")
    company = st.session_state.get("active_company")
    with st.sidebar.expander("Session", expanded=False):
        if user:
            st.write(f"**User:** {user.get('email', '')}")
        if company:
            st.write(f"**Company:** {company.get('CompanyName', '')}")
        if st.button("Logout"):
            for key in ["auth_user", "available_companies", "active_company"]:
                st.session_state.pop(key, None)
            clear_active_company_connection()
            st.rerun()


def require_login_and_company(page_title: str) -> None:
    """
    Guard function for pages.

    - If not logged in: show login form and stop.
    - If logged in but no company: show company selector and stop.
    - Otherwise: render sidebar info + logout and return.
    """
    # Ensure consistent page title (pages themselves also set titles)
    st.caption(f"Page: {page_title}")

    if "auth_user" not in st.session_state:
        render_login_form()
        st.stop()

    if "active_company" not in st.session_state:
        render_company_selector()
        st.stop()

    _render_auth_sidebar()

