"""
Question answering adapter over existing dashboard DataFrames.

This module:
- Loads key datasets via `data_loader`
- Builds a compact textual context for the LLM
- Calls `ask_llm` to get an answer grounded in that context
"""
from __future__ import annotations

from typing import List

import pandas as pd

from data_loader import (
    get_sales_summary,
    get_stock_movement,
    get_customer_profitability,
    get_split_payments,
    get_gst_sales,
    get_sessions,
)
from ml.llm_client import ask_llm, LLMError


def _summarize_df(name: str, df: pd.DataFrame, max_rows: int = 5) -> str:
    """Create a small textual summary of a DataFrame."""
    if df is None or df.empty:
        return f"### {name}\nNo data available.\n"

    # Basic schema
    schema_lines = [f"- {col}: {str(dtype)}" for col, dtype in df.dtypes.items()]
    schema_text = "\n".join(schema_lines[:25])

    # Simple numeric summary (optional)
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    desc_text = ""
    if num_cols:
        desc = df[num_cols].describe().round(2)
        desc_text = desc.to_markdown()

    # A few sample rows
    sample = df.head(max_rows)
    sample_text = sample.to_markdown(index=False)

    parts: List[str] = [
        f"### {name}",
        "Columns:",
        schema_text,
    ]
    if desc_text:
        parts.extend(["Numeric summary:", desc_text])
    parts.extend(["Sample rows:", sample_text, ""])
    return "\n".join(parts)


def build_context(question: str) -> str:
    """
    Decide which datasets to include based on the question and build context.
    """
    q = question.lower()
    sections: List[str] = []

    # Route by simple keywords
    try:
        if any(k in q for k in ["stock", "inventory", "transfer", "write off", "goods return"]):
            stk = get_stock_movement()
            sections.append(_summarize_df("Stock_Movement", stk))

        if any(k in q for k in ["customer", "free bill", "segment", "profit", "loss"]):
            cust = get_customer_profitability()
            sections.append(_summarize_df("Customer_Profitability", cust))

        if any(k in q for k in ["gst", "tax", "denomination", "till", "session", "day end"]):
            gst = get_gst_sales()
            sections.append(_summarize_df("GST_Sales", gst))
            sess = get_sessions()
            sections.append(_summarize_df("Sessions", sess))

        # Default / general sales questions
        if not sections or any(k in q for k in ["sale", "sales", "revenue", "bill", "service charge", "payment"]):
            sales = get_sales_summary()
            sections.append(_summarize_df("Sales_Summary", sales))
            split = get_split_payments()
            sections.append(_summarize_df("Split_Payments", split))
    except Exception as exc:  # pragma: no cover - defensive
        sections.append(f"Error loading some datasets: {exc}")

    return "\n".join(sections)


def answer_question(question: str) -> str:
    """
    Build context from existing DataFrames and ask the LLM.

    Returns a user-facing answer string. Any backend errors are converted to
    readable messages for the UI.
    """
    context = build_context(question)
    system_prompt = (
        "You are an analytics assistant for a restaurant POS dashboard. "
        "You must answer questions ONLY using the tabular context provided. "
        "If the data does not clearly answer the question, say so and explain "
        "what is missing. Be concise and use clear business language."
    )
    prompt = (
        "CONTEXT (from live dashboard data):\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{question}\n\n"
        "Using only the context above, answer the question. "
        "If you are not sure, state that clearly."
    )
    try:
        return ask_llm(prompt, system_prompt=system_prompt)
    except LLMError as exc:
        return f"AI error: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return f"Unexpected AI error: {exc}"

