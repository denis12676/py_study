import streamlit as st
import pandas as pd
from pricing_strategy import (
    PricingEngine, StockStrategy, ConversionStrategy,
    TurnoverStrategy, MarginStrategy, SeasonStrategy, SeasonPeriod,
)

def render_autoprices_page():
    """Отрисовка страницы автоцен"""
    st.markdown("<div class='main-header'>🤖 Автоматическое ценообразование</div>", unsafe_allow_html=True)

    tab_strat, tab_sched, tab_hist = st.tabs(["⚙️ Стратегии", "🕐 Расписание", "📋 История"])

    with tab_strat:
        st.markdown("### Настройка стратегий")
        with st.expander("📦 По остаткам", expanded=True):
            st.checkbox("Включить", value=True, key="strat_stock_on")
            st.number_input("Мало шт (порог)", value=10, key="stk_low_thr")
        
        if st.button("🔍 Рассчитать (dry-run)", type="secondary"):
            st.info("Расчет запущен...")
            # Логика вызова PricingEngine
