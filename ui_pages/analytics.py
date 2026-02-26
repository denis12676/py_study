import streamlit as st
import pandas as pd
import plotly.express as px
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def render_analytics_page():
    """Отрисовка страницы аналитики"""
    st.markdown("<div class='main-header'>📊 Аналитика продаж</div>", unsafe_allow_html=True)
    
    # Создаем вкладки для разных типов аналитики
    tab_analytics, tab_margin = st.tabs(["📈 Общая аналитика", "💰 Маржинальность"])
    
    # Вкладка 1: Общая аналитика
    with tab_analytics:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            period = st.selectbox("Период:", ["7 дней", "30 дней", "90 дней"], key="analytics_period")
            days = {"7 дней": 7, "30 дней": 30, "90 дней": 90}[period]
        
        with col2:
            detail_level = st.selectbox("Детализация:", ["Простая", "Детальная (с вычетами)"], key="analytics_detail")
        
        with col3:
            if st.button("🔄 Обновить", type="primary", key="analytics_refresh"):
                _fetch_analytics_data(days, detail_level)
    
            # Display metrics
            if st.session_state.get('revenue_data') is not None:
                _render_revenue_metrics(st.session_state.revenue_data)
                # Charts
        if 'top_products' in st.session_state and st.session_state.top_products:
            st.markdown("### 🔥 Топ товары")
            df = pd.DataFrame(st.session_state.top_products)
            fig = px.bar(df.head(10), x='name', y='revenue', title='Топ 10 товаров по выручке')
            st.plotly_chart(fig, use_container_width=True)
    
    # Вкладка 2: Маржинальность
    with tab_margin:
        _render_margin_tab()

def _fetch_analytics_data(days, detail_level):
    """Загрузка данных аналитики"""
    with st.spinner("Загрузка аналитики..."):
        try:
            if detail_level == "Детальная (с вычетами)":
                revenue = st.session_state.agent.analytics.calculate_revenue_detailed(days=days)
            else:
                revenue = st.session_state.agent.analytics.calculate_revenue(days=days)
            st.session_state.revenue_data = revenue
            
            top = st.session_state.agent.analytics.get_top_products(days=days, limit=20)
            st.session_state.top_products = top
            
            st.success("Данные обновлены!")
        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")

def _render_revenue_metrics(rev):
    """Отрисовка метрик выручки"""
    if rev is None:
        return
    if 'net_revenue' in rev:
        st.markdown("### 💰 Финансовый отчет")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Валовая выручка", f"{rev['total_revenue']:,.0f} ₽")
        col2.metric("Чистая к выплате", f"{rev['net_revenue']:,.0f} ₽")
        col3.metric("Комиссия WB", f"{rev['total_commission']:,.0f} ₽")
        col4.metric("Процент возвратов", f"{rev['return_rate']:.1f}%")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Выручка", f"{rev['total_revenue']:,.0f} ₽")
        col2.metric("Продаж", rev['total_sales'])
        col3.metric("Средний чек", f"{rev['average_check']:,.0f} ₽")

def _render_margin_tab():
    """Отрисовка вкладки маржинальности"""
    st.markdown("### 💰 Маржинальность по товарам")
    
    # Секция управления отчетами
    st.markdown("#### 📥 Загрузка отчетов из Wildberries")
    try:
        db_stats = st.session_state.agent.analytics.get_db_stats()
        if db_stats and db_stats.get('total_records') is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Записей в базе", f"{db_stats['total_records']:,}")
            col2.metric("Уникальных товаров", db_stats['unique_products'])
            col3.metric("Период данных", f"{db_stats['date_from']} - {db_stats['date_to']}" if db_stats['date_from'] else "Нет данных")
    except Exception as e:
        logger.error(f"Error rendering margin tab stats: {e}")

    if st.button("📥 Загрузить новые отчеты", type="primary"):
        with st.spinner("Загрузка отчетов из WB..."):
            try:
                result = st.session_state.agent.analytics.load_and_save_reports(days=90)
                st.success(f"✅ Загружено {result['loaded']} записей")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    # Расчет маржи
    st.markdown("---")
    if st.button("📊 Рассчитать маржинальность", key="calc_margin_btn"):
        with st.spinner("Расчет..."):
            user_id = st.session_state.user['id']
            margin_data = st.session_state.agent.analytics.get_margin_by_product(user_id, days=30)
            st.session_state.margin_data = margin_data
            if margin_data:
                st.success(f"Расчет выполнен для {len(margin_data)} товаров")
    
    if 'margin_data' in st.session_state and st.session_state.margin_data:
        df = pd.DataFrame(st.session_state.margin_data)
        st.dataframe(df, use_container_width=True)
