import streamlit as st
import pandas as pd
from typing import Any, Callable, Optional


def metric_card(label: str, value: str, subtitle: str = "") -> None:
    """Render a styled metric card (used 15+ times in dashboard.py)."""
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value'>{value}</div>
        {'<div class="metric-subtitle">' + subtitle + '</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def dataframe_with_export(df: pd.DataFrame, filename: str, title: str = "") -> None:
    """Render a dataframe with a CSV download button (used 15+ times)."""
    if title:
        st.subheader(title)
    st.dataframe(df, width='stretch')
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Скачать CSV", csv, filename, "text/csv")


def fetch_with_spinner(
    button_label: str,
    fetch_fn: Callable,
    session_key: str,
    spinner_text: str = "Загрузка...",
    success_text: Optional[str] = None,
    button_type: str = "primary",
) -> bool:
    """Render a button that loads data into session_state (used 20+ times)."""
    if st.button(button_label, type=button_type):
        with st.spinner(spinner_text):
            try:
                st.session_state[session_key] = fetch_fn()
                if success_text:
                    st.success(success_text)
                return True
            except Exception as e:
                st.error(f"Ошибка: {e}")
    return False
