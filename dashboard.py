import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_agent import WildberriesAIAgent
from wb_client import WBConfig
from managers import ProductsManager, AnalyticsManager, AdvertisingManager
from styles import get_dark_theme_css
from ui_components import metric_card, dataframe_with_export, fetch_with_spinner
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Page configuration with dark theme
st.set_page_config(
    page_title="Wildberries AI Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Custom CSS - Dark Theme (Modern Dashboard Style)
st.markdown(get_dark_theme_css(), unsafe_allow_html=True)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'products_data' not in st.session_state:
    st.session_state.products_data = None
if 'sales_data' not in st.session_state:
    st.session_state.sales_data = None
if 'ap_scheduler' not in st.session_state:
    st.session_state.ap_scheduler = None   # PriceScheduler instance
if 'ap_last_actions' not in st.session_state:
    st.session_state.ap_last_actions = []  # последние PriceAction
if 'ap_history_db' not in st.session_state:
    st.session_state.ap_history_db = None  # PriceHistoryDB instance

# Sidebar
st.sidebar.markdown("""
<style>
    .sidebar-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 1rem;
    }
    .sidebar-divider {
        border-top: 1px solid #334155;
        margin: 1rem 0;
    }
</style>
<div class='sidebar-title'>🛍️ WB AI Dashboard</div>
""", unsafe_allow_html=True)

# API Token input
if not st.session_state.agent:
    st.sidebar.markdown("### 🔑 API Токен")
    
    # Check if token exists in Streamlit secrets (for cloud deployment)
    token_from_secrets = ""
    try:
        token_from_secrets = st.secrets.get("WB_API_TOKEN", "")
    except:
        pass  # No secrets configured
    
    # Check if token exists in .env file (for local development)
    token_from_env = ""
    if not token_from_secrets:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('WB_API_TOKEN='):
                        token_from_env = line.strip().split('=', 1)[1].strip('\'"')
                        break
    
    # Determine which token to use (prioritize secrets)
    saved_token = token_from_secrets or token_from_env
    use_saved = False  # Default value
    
    if saved_token:
        # Token exists - show secure indicator but NOT the token itself
        st.sidebar.success("🔒 Токен настроен (безопасно)")
        st.sidebar.markdown("*Токен загружен из защищенного хранилища*")
        
        # Checkbox to use saved token
        use_saved = st.sidebar.checkbox("Использовать сохраненный токен", value=True)
        
        if use_saved:
            api_token = saved_token  # Use token but don't show it
            st.sidebar.markdown("<div style='color: #34d399;'>✓ Токен будет использован автоматически</div>", unsafe_allow_html=True)
        else:
            # User wants to enter new token
            api_token = st.sidebar.text_input(
                "Введите новый токен WB API:", 
                value="",
                type="password",
                placeholder="Введите токен"
            )
    else:
        # No saved token - show empty input
        api_token = st.sidebar.text_input(
            "Введите токен WB API:", 
            value="",
            type="password",
            placeholder="Введите токен"
        )
        st.sidebar.info("💡 Токен можно получить в личном кабинете WB: Профиль → API Интеграции")
    
    if st.sidebar.button("🚀 Подключиться", type="primary", use_container_width=True):
        if api_token:
            try:
                with st.spinner("Подключение к WB API..."):
                    st.session_state.agent = WildberriesAIAgent(api_token)
                    # Save to .env (only for local development)
                    try:
                        env_path = os.path.join(os.path.dirname(__file__), '.env')
                        with open(env_path, 'w', encoding='utf-8') as f:
                            f.write(f"WB_API_TOKEN={api_token}\n")
                    except:
                        pass  # Can't write in cloud environment
                st.sidebar.success("✅ Подключено!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Ошибка: {str(e)}")
        else:
            st.sidebar.warning("⚠️ Введите токен")
    
    st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
    st.sidebar.info("""
    **Как получить токен:**
    1. Личный кабинет WB
    2. Профиль → API Интеграции
    3. Создать токен
    4. Выбрать все категории
    """)
    
    # Show welcome page
    st.markdown("<div class='main-header'>🤖 Wildberries AI Agent</div>", unsafe_allow_html=True)
    st.markdown("### Введите API токен в боковой панели для начала работы")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📦 Товары
        - Каталог товаров
        - Управление ценами
        - Остатки на складах
        - Обновление карточек
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Аналитика
        - Отчеты о продажах
        - Выручка и прибыль
        - Топ товаров
        - Тренды
        """)
    
    with col3:
        st.markdown("""
        ### 📢 Реклама
        - Управление кампаниями
        - Статистика ROI
        - Ставки CPC
        - Бюджеты
        """)
    
    st.stop()
else:
    # Show connected status
    st.sidebar.markdown("### 📡 Статус")
    st.sidebar.markdown("<span class='status-online'>● Онлайн</span>", unsafe_allow_html=True)
    
    if st.sidebar.button("🚪 Отключиться"):
        st.session_state.agent = None
        st.rerun()
    
    st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

    if st.sidebar.button("API Diagnostics", use_container_width=True):
        with st.spinner("Checking API availability..."):
            health = st.session_state.agent.api.get_health_status()
        st.session_state['last_health_check'] = health

    if 'last_health_check' in st.session_state:
        health = st.session_state['last_health_check']
        st.sidebar.markdown("### API Health")
        st.sidebar.write("OK" if health.get("overall_ok") else "Issues detected")
        st.sidebar.caption(
            f"requests: {health.get('diagnostics', {}).get('total_requests', 0)} | "
            f"errors: {health.get('diagnostics', {}).get('total_errors', 0)}"
        )

# Initialize page in session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Главная"

# Compact Sidebar Navigation (like reference)
st.sidebar.markdown("""
<style>
    .nav-section {
        margin-bottom: 1.5rem;
    }
    .nav-section-title {
        color: #94a3b8;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 0 0 0.5rem 0;
        padding-left: 2.5rem;
        font-weight: 600;
    }
    .nav-item {
        display: flex;
        align-items: center;
        padding: 0.5rem 1rem;
        margin: 0.1rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s ease;
        color: #cbd5e1;
        font-size: 0.9rem;
        font-weight: 500;
        text-decoration: none;
        border: none;
        background: transparent;
        width: 100%;
    }
    .nav-item:hover {
        background-color: rgba(255, 255, 255, 0.03);
        color: #f1f5f9;
    }
    .nav-item.active {
        background-color: #8b5cf6;
        color: white;
    }
    .nav-item .icon {
        width: 18px;
        height: 18px;
        margin-right: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    }
    .nav-submenu {
        padding-left: 2.5rem;
        margin: 0;
    }
    .nav-submenu .nav-item {
        padding: 0.35rem 0.75rem;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .nav-submenu .nav-item:hover {
        color: #f1f5f9;
    }
    .nav-item .badge {
        margin-left: auto;
        background-color: #8b5cf6;
        color: white;
        font-size: 0.65rem;
        padding: 0.15rem 0.4rem;
        border-radius: 8px;
        font-weight: 600;
    }
    /* Hide button default styling */
    .stButton > button[kind="secondary"] {
        background: transparent;
        border: none;
        color: #cbd5e1;
        font-weight: 500;
        padding: 0.5rem 1rem;
        text-align: left;
        box-shadow: none;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.03);
        color: #f1f5f9;
        border: none;
        box-shadow: none;
    }
    .stButton > button[kind="primary"] {
        background: #8b5cf6;
        border: none;
        color: white;
        font-weight: 500;
        padding: 0.5rem 1rem;
        text-align: left;
        box-shadow: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #7c3aed;
        border: none;
        box-shadow: none;
    }
</style>
""", unsafe_allow_html=True)

# Analytics Section
st.sidebar.markdown("<div class='nav-section-title'>Аналитика</div>", unsafe_allow_html=True)
if st.sidebar.button("📊 Аналитика", key="nav_analytics", use_container_width=True,
             type="primary" if st.session_state.current_page == "📊 Аналитика" else "secondary"):
    st.session_state.current_page = "📊 Аналитика"
    st.rerun()

# Products Section
st.sidebar.markdown("<div class='nav-section-title'>Товары</div>", unsafe_allow_html=True)
if st.sidebar.button("📦 Товары", key="nav_products", use_container_width=True,
             type="primary" if st.session_state.current_page == "📦 Товары" else "secondary"):
    st.session_state.current_page = "📦 Товары"
    st.rerun()

# Prices Section
st.sidebar.markdown("<div class='nav-section-title'>Цены</div>", unsafe_allow_html=True)
if st.sidebar.button("💰 Управление ценами", key="nav_prices", use_container_width=True,
             type="primary" if st.session_state.current_page == "💰 Управление ценами" else "secondary"):
    st.session_state.current_page = "💰 Управление ценами"
    st.rerun()
if st.sidebar.button("🤖 Автоцены", key="nav_autoprices", use_container_width=True,
             type="primary" if st.session_state.current_page == "🤖 Автоцены" else "secondary"):
    st.session_state.current_page = "🤖 Автоцены"
    st.rerun()

# Inventory Section
st.sidebar.markdown("<div class='nav-section-title'>Склад и остатки</div>", unsafe_allow_html=True)
if st.sidebar.button("📋 Остатки", key="nav_inventory", use_container_width=True,
             type="primary" if st.session_state.current_page == "📋 Остатки" else "secondary"):
    st.session_state.current_page = "📋 Остатки"
    st.rerun()

# AI Chat Section
st.sidebar.markdown("<div class='nav-section-title'>AI Помощник</div>", unsafe_allow_html=True)
if st.sidebar.button("💬 AI Чат", key="nav_chat", use_container_width=True,
             type="primary" if st.session_state.current_page == "💬 AI Чат" else "secondary"):
    st.session_state.current_page = "💬 AI Чат"
    st.rerun()

# Marketing Section
st.sidebar.markdown("<div class='nav-section-title'>Маркетинг</div>", unsafe_allow_html=True)
if st.sidebar.button("📢 Реклама", key="nav_ads", use_container_width=True,
             type="primary" if st.session_state.current_page == "📢 Реклама" else "secondary"):
    st.session_state.current_page = "📢 Реклама"
    st.rerun()

st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

# Home
if st.sidebar.button("🏠 Главная", key="nav_home", use_container_width=True,
             type="primary" if st.session_state.current_page == "🏠 Главная" else "secondary"):
    st.session_state.current_page = "🏠 Главная"
    st.rerun()

# Cache stats in sidebar
from cache import SQLiteCache as _SQLiteCache
st.sidebar.markdown("<div class='nav-section-title'>🗄️ Кэш БД</div>", unsafe_allow_html=True)
_cache_inst = _SQLiteCache()
_stats = _cache_inst.stats()
st.sidebar.caption(
    f"✅ {_stats['alive']} записей  |  ⏳ {_stats['expired']} устаревших"
)
if st.sidebar.button("🗑️ Очистить кэш БД", key="clear_db_cache", use_container_width=True, type="secondary"):
    _cache_inst.clear()
    st.sidebar.success("Кэш очищен")
    st.rerun()
if st.sidebar.button("♻️ Удалить устаревшие", key="purge_db_cache", use_container_width=True, type="secondary"):
    removed = _cache_inst.purge_expired()
    st.sidebar.success(f"Удалено {removed} записей")
    st.rerun()

page = st.session_state.current_page

# Main content
if page == "🏠 Главная":
    # Modern header with top bar
    col_title, col_period = st.columns([3, 1])
    with col_title:
        st.markdown("<div class='main-header'>📊 Сводка по финансам</div>", unsafe_allow_html=True)
    with col_period:
        period = st.selectbox("Период:", ["7 дней", "30 дней", "90 дней"], index=1)
    
    # Top navigation tabs
    tab_ozon, tab_wb = st.tabs(["Ozon", "Wildberries"])
    
    with tab_wb:
        # Quick stats in modern card layout
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            days = {"7 дней": 7, "30 дней": 30, "90 дней": 90}[period]
            revenue = st.session_state.agent.analytics.calculate_revenue(days=days)
            
            with col1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Выручка</div>
                    <div class='metric-value'>{revenue['total_revenue']:,.0f} ₽</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Продаж</div>
                    <div class='metric-value'>{revenue['total_sales']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Средний чек</div>
                    <div class='metric-value'>{revenue['average_check']:,.0f} ₽</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                # Get products count
                products = st.session_state.agent.products.get_all_products(limit=1)
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-label'>Товаров</div>
                    <div class='metric-value'>{len(products) if products else '...'}+</div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Ошибка загрузки данных: {str(e)}")
            st.info("💡 Попробуйте обновить страницу или проверить API токен.")
        
        # Section with charts
        st.markdown("---")
        st.markdown("### 📈 Аналитика продаж")
        
        col_chart, col_info = st.columns([2, 1])
        
        with col_chart:
            try:
                # Get top products for chart
                top = st.session_state.agent.analytics.get_top_products(days=30, limit=10)
                if top:
                    df = pd.DataFrame(top)
                    fig = px.bar(
                        df, 
                        x='name', 
                        y='revenue', 
                        title='Топ товаров по выручке',
                        template='plotly_dark',
                        color_discrete_sequence=['#8b5cf6']
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='#f1f5f9'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Нет данных о продажах")
            except:
                pass
        
        with col_info:
            st.markdown("""
            <div class='info-card'>
                <h4>💡 Рекомендации от AI</h4>
                <p>Перейдите в раздел "AI Чат" чтобы получить советы по увеличению прибыли.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions in modern grid
        st.markdown("### ⚡ Быстрые действия")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📦 Показать товары", use_container_width=True):
                st.session_state.quick_action = "products"
        
        with col2:
            if st.button("💰 Выручка", use_container_width=True):
                st.session_state.quick_action = "revenue"
        
        with col3:
            if st.button("🔥 Топ товаров", use_container_width=True):
                st.session_state.quick_action = "top"
        
        with col4:
            if st.button("📢 Реклама", use_container_width=True):
                st.session_state.quick_action = "campaigns"
        
        # Second row
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Отчет за неделю", use_container_width=True):
                st.session_state.quick_action = "weekly"
        
        # Execute quick action
        if 'quick_action' in st.session_state:
            with st.spinner("Загрузка..."):
                try:
                    if st.session_state.quick_action == "products":
                        products = st.session_state.agent.products.get_all_products(limit=100)
                        if products:
                            st.success(f"Загружено {len(products)} товаров")
                            # Convert to DataFrame
                            df_data = []
                            for p in products:
                                sizes = p.get('sizes', [])
                                price = 0
                                if sizes and len(sizes) > 0:
                                    price = sizes[0].get('price', 0)
                                
                                df_data.append({
                                    'Артикул': p.get('nmID'),
                                    'Название': p.get('title', '')[:50],
                                    'Артикул продавца': p.get('vendorCode', ''),
                                    'Бренд': p.get('brand', ''),
                                    'Цена': price,
                                    'Предмет': p.get('subjectName', '')
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(
                                df,
                                use_container_width=True,
                                column_config={
                                    'Артикул': st.column_config.NumberColumn(width='small'),
                                    'Название': st.column_config.TextColumn(width='medium', max_chars=50),
                                    'Артикул продавца': st.column_config.TextColumn(width='small', max_chars=20),
                                    'Бренд': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Цена': st.column_config.NumberColumn(width='small', format='%.2f'),
                                    'Предмет': st.column_config.TextColumn(width='medium', max_chars=25),
                                }
                            )
                        else:
                            st.info("Нет данных о товарах")
                            
                    elif st.session_state.quick_action == "revenue":
                        revenue = st.session_state.agent.analytics.calculate_revenue(days=30)
                        
                        # Красивое отображение
                        st.success(f"📊 Отчет за {revenue['period_days']} дней")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("💰 Выручка", f"{revenue['total_revenue']:,.0f} ₽")
                        with col2:
                            st.metric("📦 Продаж", f"{revenue['total_sales']}")
                        with col3:
                            st.metric("📈 Средний чек", f"{revenue['average_check']:,.0f} ₽")
                        
                        st.markdown(f"### Итого: **{revenue['total_revenue']:,.2f} ₽**")
                        
                    elif st.session_state.quick_action == "top":
                        top = st.session_state.agent.analytics.get_top_products(days=30, limit=10)
                        if top:
                            df = pd.DataFrame(top)
                            fig = px.bar(df, x='name', y='revenue', title='Топ товаров по выручке')
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Нет данных о продажах")
                            
                    elif st.session_state.quick_action == "campaigns":
                        campaigns = st.session_state.agent.advertising.get_campaigns()
                        if campaigns:
                            st.success(f"Найдено {len(campaigns)} кампаний")
                            df = pd.DataFrame(campaigns)
                            st.dataframe(
                                df,
                                use_container_width=True,
                                column_config={
                                    'ID': st.column_config.NumberColumn(width='small'),
                                    'Название': st.column_config.TextColumn(width='medium', max_chars=40),
                                    'Тип': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Статус': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Ставка': st.column_config.NumberColumn(width='small', format='%d'),
                                }
                            )
                        else:
                            st.info("Нет рекламных кампаний")
                    
                    elif st.session_state.quick_action == "weekly":
                        report = st.session_state.agent.analytics.get_weekly_sales_report()
                        if report and not report.get('error'):
                            st.success(f"Отчет за неделю: {report['week_start']} - {report['week_end']}")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Выручка", f"{report['total_revenue']:,.0f} ₽")
                            col2.metric("Продаж", report['total_sales'])
                            col3.metric("Возвратов", report['total_returns'])
                            col4.metric("Средний чек", f"{report['average_check']:,.0f} ₽")
                            
                            if report.get('daily_breakdown'):
                                st.markdown("### 📈 По дням")
                                df_daily = pd.DataFrame(report['daily_breakdown'])
                                st.dataframe(
                                    df_daily,
                                    use_container_width=True,
                                    column_config={
                                        'date': st.column_config.TextColumn(width='small', max_chars=10),
                                        'revenue': st.column_config.NumberColumn(width='small', format='%.2f'),
                                        'sales': st.column_config.NumberColumn(width='small'),
                                        'returns': st.column_config.NumberColumn(width='small'),
                                    }
                                )
                            
                            if report.get('top_products'):
                                st.markdown("### 🏆 Топ товары")
                                df_products = pd.DataFrame(report['top_products'][:10])
                                st.dataframe(
                                    df_products,
                                    use_container_width=True,
                                    column_config={
                                        'nm_id': st.column_config.NumberColumn(width='small'),
                                        'name': st.column_config.TextColumn(width='medium', max_chars=40),
                                        'revenue': st.column_config.NumberColumn(width='small', format='%.2f'),
                                        'quantity': st.column_config.NumberColumn(width='small'),
                                    }
                                )
                            
                            csv_filename = st.session_state.agent.analytics.export_weekly_report_csv()
                            if csv_filename:
                                with open(csv_filename, 'rb') as f:
                                    st.download_button(
                                        label="📥 Скачать CSV",
                                        data=f,
                                        file_name=csv_filename,
                                        mime="text/csv"
                                    )
                        else:
                            st.info("Нет данных за прошлую неделю")
                            
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Rate limit" in error_msg:
                        st.error("⚠️ Превышен лимит запросов к API")
                        st.info("💡 Подождите 1-2 минуты и попробуйте снова.")
                    else:
                        st.error(f"❌ Ошибка: {error_msg}")
            
            del st.session_state.quick_action
    
    with tab_ozon:
        st.info("Интеграция с Ozon будет доступна в следующей версии.")

elif page == "💬 AI Чат":
    st.markdown("<div class='main-header'>💬 AI Ассистент Wildberries</div>", unsafe_allow_html=True)
    
    st.markdown("""
    Задавайте вопросы на естественном языке:
    - "Покажи все товары"
    - "Какая выручка за 30 дней?"
    - "Топ 5 продаваемых товаров"
    - "Запусти кампанию 12345"
    """)
    
    # Chat history
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.markdown(f"<div class='chat-message chat-user'><b>Вы:</b> {message['content']}</div>", 
                       unsafe_allow_html=True)
        else:
            # For bot messages, render as markdown with custom styling
            st.markdown(f"<div class='chat-message chat-bot'><b>AI:</b></div>", unsafe_allow_html=True)
            st.markdown(message['content'], unsafe_allow_html=False)
    
    # Input
    user_input = st.text_input("Ваш запрос:", placeholder="Например: Покажи все товары")
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        if st.button("Отправить", type="primary"):
            if user_input:
                # Add to history
                st.session_state.chat_history.append({'role': 'user', 'content': user_input})
                
                # Execute
                with st.spinner("AI обрабатывает запрос..."):
                    try:
                        result = st.session_state.agent.execute(user_input)
                        
                        # Format result for better display
                        if isinstance(result, list):
                            if len(result) == 0:
                                response = "Нет данных для отображения"
                            elif len(result) <= 3:
                                response = f"Найдено {len(result)} записей:\n\n```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
                            else:
                                response = f"Найдено {len(result)} записей. Первые 3:\n\n```json\n{json.dumps(result[:3], ensure_ascii=False, indent=2)}\n```\n\n...и еще {len(result) - 3} записей"
                        elif isinstance(result, dict):
                            if "error" in result:
                                response = f"❌ Ошибка: {result['error']}"
                            elif "week_start" in result and "total_revenue" in result:
                                # Weekly report formatting
                                response = f"""📅 **Еженедельный отчет: {result['week_start']} - {result['week_end']}**

💰 **Выручка:** {result['total_revenue']:,.2f} ₽
📦 **Продаж:** {result['total_sales']}
🔄 **Возвратов:** {result['total_returns']} ({result.get('return_rate', 0):.1f}%)
📊 **Средний чек:** {result['average_check']:,.2f} ₽"""
                            elif "total_revenue" in result and "period_days" in result:
                                # Revenue report
                                response = f"""📊 **Отчет за {result['period_days']} дней**

💰 **Выручка:** {result['total_revenue']:,.2f} ₽
📦 **Продаж:** {result['total_sales']}
📊 **Средний чек:** {result['average_check']:,.2f} ₽"""
                            else:
                                # Generic dict
                                response = f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
                        else:
                            response = str(result)
                        
                        st.session_state.chat_history.append({'role': 'bot', 'content': response})
                    except Exception as e:
                        st.session_state.chat_history.append({'role': 'bot', 'content': f"Ошибка: {str(e)}"})
                
                st.rerun()
    
    with col2:
        if st.button("Очистить чат"):
            st.session_state.chat_history = []
            st.rerun()

elif page == "📦 Товары":
    st.markdown("<div class='main-header'>📦 Управление товарами</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Каталог", "Поиск", "Цены"])
    
    with tab1:
        if st.button("🔄 Загрузить каталог", type="primary"):
            with st.spinner("Загрузка товаров..."):
                products = st.session_state.agent.products.get_all_products(limit=100)
                st.session_state.products_data = products
                if products:
                    st.success(f"Загружено {len(products)} товаров")
                    
                    # Convert to DataFrame (новый формат API)
                    df_data = []
                    for p in products:
                        # Получаем первый размер с ценой
                        sizes = p.get('sizes', [])
                        price = 0
                        if sizes and len(sizes) > 0:
                            price = sizes[0].get('price', 0)
                        
                        df_data.append({
                            'Артикул': p.get('nmID'),
                            'Название': p.get('title', '')[:50],
                            'Артикул продавца': p.get('vendorCode', ''),
                            'Бренд': p.get('brand', ''),
                            'Цена': price,
                            'Предмет': p.get('subjectName', '')
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(
                        df,
                        use_container_width=True,
                        column_config={
                            'Артикул': st.column_config.NumberColumn(width='small'),
                            'Название': st.column_config.TextColumn(width='medium', max_chars=50),
                            'Артикул продавца': st.column_config.TextColumn(width='small', max_chars=20),
                            'Бренд': st.column_config.TextColumn(width='small', max_chars=15),
                            'Цена': st.column_config.NumberColumn(width='small', format='%.2f'),
                            'Предмет': st.column_config.TextColumn(width='medium', max_chars=25),
                        }
                    )
                    
                    # Export
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Скачать CSV",
                        csv,
                        "products.csv",
                        "text/csv"
                    )
    
    with tab2:
        search_query = st.text_input("Поиск товара:", placeholder="Введите артикул или название")
        if st.button("🔍 Искать"):
            if search_query:
                with st.spinner("Поиск..."):
                    results = st.session_state.agent.products.search_products(search_query)
                    if results:
                        st.success(f"Найдено {len(results)} товаров")
                        st.json(results[:5])
                    else:
                        st.info("Ничего не найдено")
    
    with tab3:
        col1, col2, col3 = st.columns(3)
        with col1:
            nm_id = st.number_input("Артикул товара (nmID):", min_value=1, value=1)
        with col2:
            new_price = st.number_input("Новая цена:", min_value=1, value=1000)
        with col3:
            discount = st.number_input("Скидка (%):", min_value=0, max_value=95, value=0)
        
        if st.button("💾 Обновить цену", type="primary"):
            with st.spinner("Обновление..."):
                result = st.session_state.agent.products.update_price(nm_id, new_price, discount)
                st.success("Цена обновлена!")
                st.json(result)

elif page == "📋 Остатки":
    st.markdown("<div class='main-header'>📋 Остатки товаров</div>", unsafe_allow_html=True)
    
    tab_fbs, tab_fbo, tab_summary = st.tabs(["FBS (склад продавца)", "FBO (склад WB)", "Сводка по артикулам"])
    
    with tab_fbs:
        st.markdown("### 📦 Остатки на складе продавца (FBS)")
        
        if st.button("🔄 Загрузить склады", type="primary", key="fbs_load_warehouses"):
            with st.spinner("Загрузка складов..."):
                try:
                    warehouses = st.session_state.agent.inventory.get_warehouses()
                    st.session_state.fbs_warehouses = warehouses
                    if warehouses:
                        st.success(f"Найдено {len(warehouses)} складов")
                    else:
                        st.info("Нет складов")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        
        if 'fbs_warehouses' in st.session_state and st.session_state.fbs_warehouses:
            warehouse_options = {w.get('name', f"Склад {w.get('id')}"): w.get('id') 
                               for w in st.session_state.fbs_warehouses}
            
            selected_warehouse = st.selectbox(
                "Выберите склад:",
                options=list(warehouse_options.keys()),
                key="fbs_warehouse_select"
            )
            
            warehouse_id = warehouse_options[selected_warehouse]
            
            if st.button("📥 Загрузить остатки", type="primary", key="fbs_load_stocks"):
                with st.spinner("Загрузка остатков..."):
                    try:
                        stocks = st.session_state.agent.inventory.get_stocks(warehouse_id)
                        st.session_state.fbs_stocks = stocks
                        
                        if stocks:
                            st.success(f"Загружено {len(stocks)} позиций")
                            
                            df_data = []
                            for s in stocks:
                                df_data.append({
                                    'Баркод': s.get('sku', ''),
                                    'Артикул продавца': s.get('vendorCode', ''),
                                    'Артикул WB': s.get('nmId', ''),
                                    'Название': s.get('title', '')[:50],
                                    'Бренд': s.get('brand', ''),
                                    'Размер': s.get('techSize', ''),
                                    'Остаток': s.get('amount', 0),
                                    'В пути': s.get('inTransit', 0)
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(
                                df,
                                use_container_width=True,
                                column_config={
                                    'Баркод': st.column_config.TextColumn(width='small', max_chars=20),
                                    'Артикул продавца': st.column_config.TextColumn(width='small', max_chars=20),
                                    'Артикул WB': st.column_config.NumberColumn(width='small'),
                                    'Название': st.column_config.TextColumn(width='medium', max_chars=50),
                                    'Бренд': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Размер': st.column_config.TextColumn(width='small', max_chars=10),
                                    'Остаток': st.column_config.NumberColumn(width='small'),
                                    'В пути': st.column_config.NumberColumn(width='small'),
                                }
                            )
                            
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📥 Скачать CSV",
                                csv,
                                "fbs_stocks.csv",
                                "text/csv",
                                key="fbs_download"
                            )
                        else:
                            st.info("Нет данных об остатках")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
    
    with tab_fbo:
        st.markdown("### 🏭 Остатки на складах WB (FBO)")
        st.markdown("*Полная информация по остаткам на всех складах Wildberries*")
        
        # Показываем время последнего обновления если есть
        if 'fbo_stocks_timestamp' in st.session_state:
            last_update = st.session_state.fbo_stocks_timestamp
            st.caption(f"🕐 Последнее обновление: {last_update}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            force_refresh = st.checkbox("🔄 Принудительное обновление (игнорировать кеш)", value=False)
        with col2:
            if st.button("🗑️ Очистить кеш", type="secondary"):
                st.session_state.agent.inventory.clear_fbo_cache()
                st.success("Кеш очищен!")
        
        if st.button("📦 Загрузить остатки FBO", type="primary", key="fbo_load"):
            with st.spinner("Загрузка остатков FBO через Statistics API..."):
                try:
                    logger.debug("Старт загрузки остатков FBO через get_fbo_stocks()")
                    
                    # Используем новый метод с Statistics API
                    stocks = st.session_state.agent.inventory.get_fbo_stocks(
                        use_cache=not force_refresh,
                        force_refresh=force_refresh
                    )
                    
                    logger.debug("get_fbo_stocks() вернул %s записей", len(stocks) if isinstance(stocks, list) else 'не-список')
                    st.session_state.fbo_stocks = stocks
                    st.session_state.fbo_stocks_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    
                    if stocks:
                        st.success(f"✅ Загружено {len(stocks)} записей")
                        
                        # Группируем по складам для отображения
                        by_warehouse = {}
                        for s in stocks:
                            wh = s.get('warehouseName', 'Неизвестно')
                            by_warehouse[wh] = by_warehouse.get(wh, 0) + 1
                        
                        # Показываем статистику по складам
                        st.markdown("**📊 Распределение по складам:**")
                        cols = st.columns(min(len(by_warehouse), 4))
                        for i, (warehouse, count) in enumerate(by_warehouse.items()):
                            with cols[i % 4]:
                                st.metric(warehouse, f"{count} товаров")
                        
                        # Создаем DataFrame с полными данными
                        df_data = []
                        for s in stocks:
                            df_data.append({
                                'Артикул WB': s.get('nmId', ''),
                                'Артикул продавца': s.get('supplierArticle', ''),
                                'Баркод': s.get('barcode', ''),
                                'Склад': s.get('warehouseName', ''),
                                'Доступно': s.get('quantity', 0),
                                'В пути до клиента': s.get('inWayToClient', 0),
                                'В пути от клиента': s.get('inWayFromClient', 0),
                                'Всего': s.get('quantityFull', 0),
                                'Категория': s.get('category', ''),
                                'Предмет': s.get('subject', ''),
                                'Бренд': s.get('brand', ''),
                                'Размер': s.get('techSize', ''),
                                'Цена': s.get('Price', 0),
                                'Скидка %': s.get('Discount', 0),
                            })
                        
                        df_full = pd.DataFrame(df_data)
                        
                        # Select only essential columns to prevent overflow
                        essential_columns = [
                            'Артикул WB', 'Артикул продавца', 'Склад', 
                            'Доступно', 'Всего', 'Бренд', 'Цена'
                        ]
                        df = df_full[essential_columns].copy()
                        
                        # Фильтр по складу
                        all_warehouses = ['Все'] + sorted(df['Склад'].unique().tolist())
                        selected_warehouse = st.selectbox("📍 Фильтр по складу:", all_warehouses)
                        
                        if selected_warehouse != 'Все':
                            df_filtered = df[df['Склад'] == selected_warehouse]
                            st.dataframe(
                                df_filtered,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    'Артикул WB': st.column_config.NumberColumn(width='small', format='%d'),
                                    'Артикул продавца': st.column_config.TextColumn(width='small', max_chars=20),
                                    'Склад': st.column_config.TextColumn(width='medium', max_chars=30),
                                    'Доступно': st.column_config.NumberColumn(width='small'),
                                    'Всего': st.column_config.NumberColumn(width='small'),
                                    'Бренд': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Цена': st.column_config.NumberColumn(width='small', format='%.2f'),
                                }
                            )
                        else:
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    'Артикул WB': st.column_config.NumberColumn(width='small', format='%d'),
                                    'Артикул продавца': st.column_config.TextColumn(width='small', max_chars=20),
                                    'Склад': st.column_config.TextColumn(width='medium', max_chars=30),
                                    'Доступно': st.column_config.NumberColumn(width='small'),
                                    'Всего': st.column_config.NumberColumn(width='small'),
                                    'Бренд': st.column_config.TextColumn(width='small', max_chars=15),
                                    'Размер': st.column_config.TextColumn(width='small', max_chars=10),
                                    'Цена': st.column_config.NumberColumn(width='small', format='%.2f'),
                                    'Скидка %': st.column_config.NumberColumn(width='small'),
                                }
                            )
                        
                        # Статистика
                        total_quantity = df['Доступно'].sum()
                        total_full = df['Всего'].sum()
                        col1, col2, col3 = st.columns(3)
                        col1.metric("📦 Всего товаров", len(df))
                        col2.metric("📊 Доступно для продажи", int(total_quantity))
                        col3.metric("🔄 Полный остаток", int(total_full))
                        
                        # Скачать CSV (только основные поля)
                        df_simple = df[['Артикул продавца', 'Артикул WB', 'Доступно', 'Склад']].copy()
                        csv = df_simple.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Скачать CSV (артикул + количество)",
                            csv,
                            "fbo_stocks_simple.csv",
                            "text/csv",
                            key="fbo_simple_download"
                        )
                        
                        # Скачать CSV (полные данные)
                        csv_full = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Скачать CSV (полные данные)",
                            csv_full,
                            "fbo_stocks_full.csv",
                            "text/csv",
                            key="fbo_full_download"
                        )
                    else:
                        logger.warning("get_fbo_stocks() вернул пустой список")
                        st.info("ℹ️ Нет данных о остатках FBO. Возможные причины:\n\n"
                               "1. Нет активных товаров на складах WB\n"
                               "2. Временные проблемы с API\n"
                               "3. Rate limit - попробуйте через минуту")
                        
                except Exception as e:
                    logger.error("Исключение при загрузке остатков FBO: %s", e, exc_info=True)
                    import traceback
                    traceback.print_exc()
                    st.error(f"❌ Ошибка загрузки: {e}")
                    st.code(traceback.format_exc())


    with tab_summary:
        st.markdown("### Сводка остатков по всем артикулам (FBS + FBO)")
        st.caption("Таблица собирается по всем складам и всем артикулам")

        if st.button("Собрать сводную таблицу", type="primary", key="stocks_summary_build"):
            with st.spinner("Собираем остатки FBS и FBO..."):
                try:
                    # FBS: aggregate by (nmId, vendorCode)
                    fbs_by_key = {}
                    all_fbs_stocks = st.session_state.agent.inventory.get_all_fbs_stocks()
                    for _, stocks in all_fbs_stocks.items():
                        for stock in stocks:
                            nm_id = stock.get("nmId")
                            article = str(stock.get("vendorCode", "") or "").strip()
                            key = (nm_id, article)
                            qty = int(stock.get("amount", 0) or 0)
                            fbs_by_key[key] = fbs_by_key.get(key, 0) + qty

                    # FBO: aggregate by (nmId, supplierArticle)
                    fbo_by_key = {}
                    fbo_stocks = st.session_state.agent.inventory.get_fbo_stocks(use_cache=True, force_refresh=False)
                    for stock in fbo_stocks:
                        nm_id = stock.get("nmId")
                        article = str(stock.get("supplierArticle", "") or "").strip()
                        key = (nm_id, article)
                        qty = int(stock.get("quantity", 0) or 0)
                        fbo_by_key[key] = fbo_by_key.get(key, 0) + qty

                    all_keys = set(fbs_by_key.keys()) | set(fbo_by_key.keys())
                    rows = []
                    for nm_id, article in all_keys:
                        fbs_qty = fbs_by_key.get((nm_id, article), 0)
                        fbo_qty = fbo_by_key.get((nm_id, article), 0)
                        total_qty = fbs_qty + fbo_qty
                        rows.append({
                            "Артикул": article,
                            "nmID": nm_id,
                            "Остаток FBS": fbs_qty,
                            "Остаток FBO": fbo_qty,
                            "Общий остаток": total_qty,
                        })

                    if rows:
                        df_summary = pd.DataFrame(rows)
                        nm_ids_series = pd.to_numeric(df_summary["nmID"], errors="coerce").dropna().astype(int)
                        nm_ids = sorted({int(v) for v in nm_ids_series.tolist() if int(v) > 0})
                        avg_orders_map = st.session_state.agent.analytics.get_avg_orders_by_nm_ids(nm_ids, days=30, stock_type="")

                        nm_id_numeric = pd.to_numeric(df_summary["nmID"], errors="coerce")
                        df_summary["Скорость заказов в день"] = nm_id_numeric.map(
                            lambda x: round(float(avg_orders_map.get(int(x), 0)), 2) if pd.notna(x) else 0.0
                        )
                        df_summary["На сколько дней хватит"] = df_summary.apply(
                            lambda r: round((r["Общий остаток"] / r["Скорость заказов в день"]), 1)
                            if r["Скорость заказов в день"] > 0 else None,
                            axis=1
                        )

                        df_summary = df_summary.sort_values(by=["Общий остаток", "Артикул"], ascending=[False, True])
                        st.dataframe(df_summary, use_container_width=True, hide_index=True)

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Артикулов", len(df_summary))
                        col2.metric("Суммарный FBS", int(df_summary["Остаток FBS"].sum()))
                        col3.metric("Суммарный FBO", int(df_summary["Остаток FBO"].sum()))

                        csv = df_summary.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Скачать CSV",
                            csv,
                            "stocks_summary_all_articles.csv",
                            "text/csv",
                            key="stocks_summary_download",
                        )
                    else:
                        st.info("Данные по остаткам не найдены")
                except Exception as e:
                    st.error(f"Ошибка при построении сводки: {e}")

elif page == "📊 Аналитика":
    st.markdown("<div class='main-header'>📊 Аналитика продаж</div>", unsafe_allow_html=True)
    
    # Создаем вкладки для разных типов аналитики
    tab_analytics, tab_margin = st.tabs(["📈 Общая аналитика", "💰 Маржинальность"])
    
    # Вкладка 1: Общая аналитика (существующий функционал)
    with tab_analytics:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            period = st.selectbox("Период:", ["7 дней", "30 дней", "90 дней"], key="analytics_period")
            days = {"7 дней": 7, "30 дней": 30, "90 дней": 90}[period]
        
        with col2:
            detail_level = st.selectbox("Детализация:", ["Простая", "Детальная (с вычетами)"], key="analytics_detail")
        
        with col3:
            if st.button("🔄 Обновить", type="primary", key="analytics_refresh"):
                with st.spinner("Загрузка аналитики..."):
                    try:
                        # Revenue
                        if detail_level == "Детальная (с вычетами)":
                            revenue = st.session_state.agent.analytics.calculate_revenue_detailed(days=days)
                        else:
                            revenue = st.session_state.agent.analytics.calculate_revenue(days=days)
                        st.session_state.revenue_data = revenue
                        
                        # Top products
                        top = st.session_state.agent.analytics.get_top_products(days=days, limit=20)
                        st.session_state.top_products = top
                        
                        # Sales data
                        sales = st.session_state.agent.analytics.get_sales(
                            date_from=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                        )
                        st.session_state.sales_data = sales
                        
                        st.success("Данные обновлены!")
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Слишком много" in error_msg or "Rate limit" in error_msg:
                            st.error("⚠️ Превышен лимит запросов к API Wildberries")
                            st.info("💡 Пожалуйста, подождите 1-2 минуты и попробуйте снова. API статистики имеет ограничение: 1 запрос в минуту.")
                        else:
                            st.error(f"❌ Ошибка загрузки данных: {error_msg}")
    
    with col3:
        if st.button("🔄 Обновить", type="primary"):
            with st.spinner("Загрузка аналитики..."):
                try:
                    # Revenue
                    if detail_level == "Детальная (с вычетами)":
                        revenue = st.session_state.agent.analytics.calculate_revenue_detailed(days=days)
                    else:
                        revenue = st.session_state.agent.analytics.calculate_revenue(days=days)
                    st.session_state.revenue_data = revenue
                    
                    # Top products
                    top = st.session_state.agent.analytics.get_top_products(days=days, limit=20)
                    st.session_state.top_products = top
                    
                    # Sales data
                    sales = st.session_state.agent.analytics.get_sales(
                        date_from=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                    )
                    st.session_state.sales_data = sales
                    
                    st.success("Данные обновлены!")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Слишком много" in error_msg or "Rate limit" in error_msg:
                        st.error("⚠️ Превышен лимит запросов к API Wildberries")
                        st.info("💡 Пожалуйста, подождите 1-2 минуты и попробуйте снова. API статистики имеет ограничение: 1 запрос в минуту.")
                    else:
                        st.error(f"❌ Ошибка загрузки данных: {error_msg}")
    
    # Display metrics
    if 'revenue_data' in st.session_state:
        rev = st.session_state.revenue_data
        
        # Проверяем какой формат данных (простой или детальный)
        if 'net_revenue' in rev:
            # Детальный формат
            st.markdown("### 💰 Финансовый отчет")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Валовая выручка", f"{rev['total_revenue']:,.0f} ₽")
            with col2:
                st.metric("Чистая к выплате", f"{rev['net_revenue']:,.0f} ₽", 
                         delta=f"{((rev['net_revenue']/rev['total_revenue']-1)*100):.1f}%" if rev['total_revenue'] > 0 else "")
            with col3:
                st.metric("Комиссия WB", f"{rev['total_commission']:,.0f} ₽")
            with col4:
                st.metric("Процент возвратов", f"{rev['return_rate']:.1f}%")
            
            # Детальная таблица
            with st.expander("📋 Детальная информация"):
                details_data = {
                    "Показатель": [
                        "Валовая выручка (без возвратов)",
                        "Возвраты (сумма)",
                        "Чистая к выплате",
                        "Комиссия WB",
                        "Логистика",
                        "Хранение",
                        "Штрафы",
                        "Количество продаж",
                        "Количество возвратов",
                        "Всего операций",
                        "Средний чек (валовой)",
                        "Средний чек (чистый)",
                        "Процент возвратов"
                    ],
                    "Значение": [
                        f"{rev['total_revenue']:,.2f} ₽",
                        f"{rev['total_returns']:,.2f} ₽",
                        f"{rev['net_revenue']:,.2f} ₽",
                        f"{rev['total_commission']:,.2f} ₽",
                        f"{rev['total_logistics']:,.2f} ₽",
                        f"{rev['total_storage']:,.2f} ₽",
                        f"{rev['penalty']:,.2f} ₽",
                        f"{rev['total_sales']}",
                        f"{rev['total_returns_count']}",
                        f"{rev['total_operations']}",
                        f"{rev['average_check']:,.2f} ₽",
                        f"{rev['average_net_check']:,.2f} ₽",
                        f"{rev['return_rate']:.2f}%"
                    ]
                }
                df_details = pd.DataFrame(details_data)
                st.dataframe(
                    df_details,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        'Показатель': st.column_config.TextColumn(width='medium', max_chars=40),
                        'Значение': st.column_config.TextColumn(width='medium', max_chars=40),
                    }
                )
        else:
            # Простой формат
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Выручка", f"{rev['total_revenue']:,.0f} ₽")
            with col2:
                st.metric("Продаж", rev['total_sales'])
            with col3:
                st.metric("Средний чек", f"{rev['average_check']:,.0f} ₽")
    
    # Charts
    if 'top_products' in st.session_state and st.session_state.top_products:
        st.markdown("### 🔥 Топ товары")
        df = pd.DataFrame(st.session_state.top_products)
        
        fig = px.bar(
            df.head(10), 
            x='name', 
            y='revenue',
            title='Топ 10 товаров по выручке',
            labels={'name': 'Товар', 'revenue': 'Выручка (₽)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Вкладка 2: Маржинальность по товарам
    with tab_margin:
        st.markdown("### 💰 Маржинальность по товарам")
        st.markdown("""
        Расчет на основе детального отчета WB. 
        
        **Как работать:**
        1. Сначала загрузите отчеты из WB (один раз)
        2. Затем рассчитывайте маржу (мгновенно из локальной базы)
        """)
        
        # === СЕКЦИЯ УПРАВЛЕНИЯ ОТЧЕТАМИ ===
        st.markdown("---")
        st.markdown("#### 📥 Загрузка отчетов из Wildberries")
        
        # Проверяем статус базы данных
        try:
            db_stats = st.session_state.agent.analytics.get_db_stats()
            
            col_db1, col_db2, col_db3 = st.columns(3)
            with col_db1:
                st.metric("Записей в базе", f"{db_stats['total_records']:,}")
            with col_db2:
                st.metric("Уникальных товаров", db_stats['unique_products'])
            with col_db3:
                date_range_text = ""
                if db_stats['date_from'] and db_stats['date_to']:
                    date_range_text = f"{db_stats['date_from']} - {db_stats['date_to']}"
                st.metric("Период данных", date_range_text if date_range_text else "Нет данных")
            
        except Exception as e:
            st.warning(f"Не удалось получить статистику БД: {e}")
        
        # Кнопка загрузки отчетов
        col_load1, col_load2 = st.columns([2, 1])
        
        with col_load1:
            load_days = st.selectbox(
                "Загрузить отчеты за:",
                ["30 дней", "60 дней", "90 дней", "180 дней"],
                index=2,
                key="load_reports_days"
            )
            load_days_num = {"30 дней": 30, "60 дней": 60, "90 дней": 90, "180 дней": 180}[load_days]
        
        with col_load2:
            if st.button("📥 Загрузить отчеты", type="primary", key="load_reports_btn"):
                with st.spinner(f"Загрузка отчетов за {load_days_num} дней из WB... Это может занять 2-3 минуты..."):
                    try:
                        # Очищаем старые данные перед загрузкой новых
                        if st.checkbox("Очистить старые данные перед загрузкой", value=True, key="clear_old_data"):
                            import sqlite3
                            from pathlib import Path
                            db_path = Path(__file__).parent / "wb_cache.db"
                            conn = sqlite3.connect(str(db_path), check_same_thread=False)
                            conn.execute("DELETE FROM financial_reports")
                            conn.commit()
                            conn.close()
                            st.info("Старые данные очищены")
                        
                        # Загружаем отчеты
                        result = st.session_state.agent.analytics.load_and_save_reports(days=load_days_num)
                        
                        st.success(f"✅ Загружено {result['loaded']} записей, сохранено {result['saved']}, ошибок: {result['errors']}")
                        st.info(f"Период: {result['date_from']} - {result['date_to']}")
                        
                        # Обновляем страницу для отображения новой статистики
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Ошибка загрузки: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # === СЕКЦИЯ РАСЧЕТА МАРЖИ ===
        st.markdown("---")
        st.markdown("#### 📊 Расчет маржинальности")
        
        col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
        
        with col_m1:
            margin_period = st.selectbox("Период анализа:", ["7 дней", "30 дней", "90 дней"], key="margin_period")
            margin_days = {"7 дней": 7, "30 дней": 30, "90 дней": 90}[margin_period]
        
        with col_m2:
            min_revenue = st.number_input("Мин. выручка (₽):", min_value=0, value=0, step=1000, key="min_revenue")
        
        with col_m3:
            if st.button("📊 Рассчитать", type="primary", key="margin_refresh"):
                with st.spinner("Расчет маржинальности из локальной базы..."):
                    try:
                        # Расчет из локальной БД (быстро!)
                        margin_data = st.session_state.agent.analytics.get_margin_by_product(
                            days=margin_days, 
                            use_local_db=True
                        )
                        st.session_state.margin_data = margin_data
                        
                        if margin_data:
                            st.success(f"✅ Расчет выполнен: {len(margin_data)} товаров")
                        else:
                            st.warning("⚠️ Нет данных за выбранный период. Загрузите отчеты из WB.")
                            
                    except Exception as e:
                        error_msg = str(e)
                        st.error(f"❌ Ошибка: {error_msg}")
                        import traceback
                        st.code(traceback.format_exc())
                        
                        if margin_data:
                            st.success(f"✅ Загружено {len(margin_data)} товаров с продажами")
                        else:
                            st.warning("⚠️ Загружено 0 товаров. Проверьте наличие продаж за выбранный период.")
                            
                    except Exception as e:
                        error_msg = str(e)
                        st.error(f"❌ Ошибка: {error_msg}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # Отображение таблицы маржинальности
        if 'margin_data' in st.session_state and st.session_state.margin_data:
            df_data = []
            for item in st.session_state.margin_data:
                # Фильтр по минимальной выручке
                if item['gross_revenue'] < min_revenue:
                    continue
                    
                df_data.append({
                    'Артикул WB': item['nm_id'],
                    'Артикул продавца': item['vendor_code'],
                    'Предмет': item['subject'],
                    'Бренд': item['brand'],
                    'Продажи': item['sales_count'],
                    'Возвраты': item['returns_count'],
                    'Возврат %': f"{item['return_rate']:.1f}%",
                    'Выручка': item['gross_revenue'],
                    'К выплате': item['net_payout'],
                    'Расходы WB': item['total_wb_costs'],
                    'Комиссия': item['wb_commission'],
                    'Логистика': item['logistics_cost'],
                    'Хранение': item['storage_cost'],
                    'Штрафы': item['penalties'],
                    'Ср. цена': item['avg_retail_price'],
                    '% расходов': f"{item['wb_cost_rate']:.1f}%",
                    '% к выплате': f"{item['net_payout_rate']:.1f}%",
                })
            
            if df_data:
                df = pd.DataFrame(df_data)
                
                # Итоговая статистика
                total_revenue = sum(item['gross_revenue'] for item in st.session_state.margin_data)
                total_payout = sum(item['net_payout'] for item in st.session_state.margin_data)
                total_costs = sum(item['total_wb_costs'] for item in st.session_state.margin_data)
                avg_cost_rate = (total_costs / total_revenue * 100) if total_revenue > 0 else 0
                
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric("Общая выручка", f"{total_revenue:,.0f} ₽")
                with col_stat2:
                    st.metric("К выплате", f"{total_payout:,.0f} ₽")
                with col_stat3:
                    st.metric("Расходы WB", f"{total_costs:,.0f} ₽")
                with col_stat4:
                    st.metric("Средний % расходов", f"{avg_cost_rate:.1f}%")
                
                # Таблица
                st.markdown("#### 📋 Детализация по товарам")
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        'Артикул WB': st.column_config.NumberColumn(width='small'),
                        'Артикул продавца': st.column_config.TextColumn(width='medium'),
                        'Предмет': st.column_config.TextColumn(width='medium'),
                        'Бренд': st.column_config.TextColumn(width='small'),
                        'Продажи': st.column_config.NumberColumn(width='small'),
                        'Возвраты': st.column_config.NumberColumn(width='small'),
                        'Возврат %': st.column_config.TextColumn(width='small'),
                        'Выручка': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'К выплате': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Расходы WB': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Комиссия': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Логистика': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Хранение': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Штрафы': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        'Ср. цена': st.column_config.NumberColumn(width='small', format='%d ₽'),
                        '% расходов': st.column_config.TextColumn(width='small'),
                        '% к выплате': st.column_config.TextColumn(width='small'),
                    },
                    hide_index=True
                )
                
                # CSV экспорт
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Скачать CSV",
                    csv,
                    f"margin_analysis_{margin_days}days.csv",
                    "text/csv",
                    key="margin_csv_download"
                )
            else:
                st.info(f"ℹ️ Нет товаров с выручкой выше {min_revenue} ₽")

elif page == "📢 Реклама":
    st.markdown("<div class='main-header'>📢 Управление рекламой</div>", unsafe_allow_html=True)
    
    if st.button("🔄 Загрузить кампании", type="primary"):
        with st.spinner("Загрузка..."):
            campaigns = st.session_state.agent.advertising.get_campaigns()
            st.session_state.campaigns_data = campaigns
            if campaigns:
                st.success(f"Найдено {len(campaigns)} кампаний")
                
                # Display table
                df_data = []
                for c in campaigns:
                    status_map = {4: "Готова", 7: "Активна", 9: "Завершена", 11: "Пауза"}
                    type_map = {4: "Каталог", 5: "Карточка", 6: "Поиск", 7: "Рекомендации"}
                    
                    df_data.append({
                        'ID': c.get('advertId'),
                        'Название': c.get('name', ''),
                        'Тип': type_map.get(c.get('type'), c.get('type')),
                        'Статус': status_map.get(c.get('status'), c.get('status')),
                        'Ставка': c.get('cpm', 0)
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        'ID': st.column_config.NumberColumn(width='small'),
                        'Название': st.column_config.TextColumn(width='medium', max_chars=40),
                        'Тип': st.column_config.TextColumn(width='small', max_chars=15),
                        'Статус': st.column_config.TextColumn(width='small', max_chars=15),
                        'Ставка': st.column_config.NumberColumn(width='small', format='%d'),
                    }
                )
            else:
                st.info("Нет рекламных кампаний")
    
    # Campaign management
    if 'campaigns_data' in st.session_state and st.session_state.campaigns_data:
        st.markdown("### ⚙️ Управление кампаниями")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            campaign_id = st.number_input("ID кампании:", min_value=1)
        
        with col2:
            action = st.selectbox("Действие:", ["Запустить", "Остановить", "Удалить"])
        
        with col3:
            if action == "Запустить":
                if st.button("▶️ Запустить", type="primary"):
                    with st.spinner("Запуск..."):
                        success = st.session_state.agent.advertising.start_campaign(campaign_id)
                        if success:
                            st.success("Кампания запущена!")
                        else:
                            st.error("Не удалось запустить")
            
            elif action == "Остановить":
                if st.button("⏸️ Остановить", type="primary"):
                    with st.spinner("Остановка..."):
                        success = st.session_state.agent.advertising.pause_campaign(campaign_id)
                        if success:
                            st.success("Кампания остановлена!")
                        else:
                            st.error("Не удалось остановить")
            
            elif action == "Удалить":
                if st.button("🗑️ Удалить", type="primary"):
                    with st.spinner("Удаление..."):
                        success = st.session_state.agent.advertising.delete_campaign(campaign_id)
                        if success:
                            st.success("Кампания удалена!")
                        else:
                            st.error("Не удалось удалить")

elif page == "💰 Управление ценами":
    st.markdown("<div class='main-header'>💰 Управление ценами</div>", unsafe_allow_html=True)
    
    # Инициализация session state
    if 'price_edit_data' not in st.session_state:
        st.session_state.price_edit_data = {}
    if 'price_products_loaded' not in st.session_state:
        st.session_state.price_products_loaded = False
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = set()
    if 'price_current_page' not in st.session_state:
        st.session_state.price_current_page = 1
    
    # Фильтры и кнопки действий
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    
    with col1:
        search_query = st.text_input("🔍 Поиск по артикулу или названию:", placeholder="Введите запрос...")
    
    with col2:
        items_per_page = st.selectbox("На странице:", [20, 50, 100], index=0)
    
    with col3:
        if st.button("🔄 Загрузить", type="primary", use_container_width=True):
            st.session_state.price_products_loaded = False
            st.session_state.price_edit_data = {}
            st.session_state.selected_products = set()
            st.session_state.price_current_page = 1
    
    with col4:
        # Кнопка отправки изменений (активна только при выборе товаров)
        selected_count = len(st.session_state.selected_products)
        if selected_count > 0:
            if st.button(f"✅ Отправить ({selected_count})", type="primary", use_container_width=True):
                # Отправляем только выбранные товары
                changes = []
                for nm_id in st.session_state.selected_products:
                    edit_data = st.session_state.price_edit_data.get(nm_id, {})
                    price = edit_data.get('price', 0)
                    discounted = edit_data.get('discountedPrice', price)
                    discount = edit_data.get('discount', 0)
                    
                    if price > 0:
                        changes.append({
                            'nmID': nm_id,
                            'price': int(price),
                            'discount': discount
                        })
                
                if changes:
                    with st.spinner(f"Отправка {len(changes)} товаров..."):
                        try:
                            result = st.session_state.agent.products.update_multiple_prices(changes)
                            st.success(f"✅ Цены обновлены! ID загрузки: {result.get('data', {}).get('uploadID', 'N/A')}")
                            st.session_state.selected_products = set()
                            st.session_state.price_products_loaded = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ошибка: {e}")
    
    # Загрузка товаров
    if not st.session_state.price_products_loaded:
        with st.spinner("Загрузка товаров..."):
            try:
                # Загружаем все товары сразу (до 1000)
                products = st.session_state.agent.products.get_products_with_photos_and_prices(
                    limit=1000,
                    search=search_query if search_query else None
                )
                st.session_state.price_products_all = products
                st.session_state.price_products_loaded = True
                
                # Инициализируем данные для редактирования
                for p in products:
                    nm_id = p['nmID']
                    if nm_id not in st.session_state.price_edit_data:
                        st.session_state.price_edit_data[nm_id] = {
                            'price': p['price'],
                            'discountedPrice': p['discountedPrice'],
                            'discount': p['discount']
                        }
                
                if products:
                    st.success(f"✅ Загружено {len(products)} товаров")
                else:
                    st.info("ℹ️ Товары не найдены")
                    
            except Exception as e:
                st.error(f"❌ Ошибка загрузки: {e}")
    
    # Отображение таблицы
    if st.session_state.price_products_loaded and st.session_state.get('price_products_all'):
        all_products = st.session_state.price_products_all
        total_products = len(all_products)
        
        # Пагинация
        total_pages = max(1, (total_products + items_per_page - 1) // items_per_page)
        current_page = st.session_state.price_current_page
        
        # Получаем товары для текущей страницы
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_products)
        products = all_products[start_idx:end_idx]
        
        # Заголовок таблицы с счетчиками
        col_counter, col_pagination = st.columns([2, 3])
        
        with col_counter:
            selected_count = len(st.session_state.selected_products)
            st.markdown(f"**Всего: {total_products} | Выбрано: {selected_count}**")
        
        with col_pagination:
            # Кнопки пагинации
            cols = st.columns([1, 1, 3, 1, 1])
            with cols[0]:
                if st.button("◀", disabled=current_page <= 1):
                    st.session_state.price_current_page -= 1
                    st.rerun()
            with cols[1]:
                st.markdown(f"**{current_page} / {total_pages}**", unsafe_allow_html=True)
            with cols[3]:
                if st.button("▶", disabled=current_page >= total_pages):
                    st.session_state.price_current_page += 1
                    st.rerun()
        
        # Шапка таблицы
        st.markdown("""
        <style>
            .price-table-header {
                background-color: #1e293b;
                padding: 10px;
                border-radius: 6px;
                font-weight: 600;
                color: #94a3b8;
                margin-bottom: 5px;
            }
            .price-table-row {
                background-color: rgba(30, 41, 59, 0.3);
                padding: 8px;
                border-radius: 6px;
                margin-bottom: 5px;
                border: 1px solid #334155;
                transition: all 0.2s;
            }
            .price-table-row:hover {
                background-color: rgba(30, 41, 59, 0.5);
                border-color: #8b5cf6;
            }
            .price-table-row.selected {
                background-color: rgba(139, 92, 246, 0.1);
                border-color: #8b5cf6;
            }
            .product-img {
                width: 50px;
                height: 50px;
                object-fit: cover;
                border-radius: 4px;
            }
        </style>
        <div class="price-table-header">
            <div style="display: grid; grid-template-columns: 40px 70px 2fr 120px 100px 120px; gap: 10px; align-items: center;">
                <div><input type="checkbox" disabled></div>
                <div>Фото</div>
                <div>Товар</div>
                <div>Цена без скидки</div>
                <div>Скидка</div>
                <div>Цена со скидкой</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Строки таблицы
        for p in products:
            nm_id = p['nmID']
            is_selected = nm_id in st.session_state.selected_products
            edit_data = st.session_state.price_edit_data.get(nm_id, {})
            
            # Цвет фона для выбранных
            row_class = "price-table-row selected" if is_selected else "price-table-row"
            
            # Создаем строку товара
            col_checkbox, col_photo, col_info, col_price, col_discount, col_discounted = st.columns([0.5, 0.8, 2.5, 1.2, 1, 1.5])
            
            with col_checkbox:
                checkbox_key = f"chk_{nm_id}"
                is_checked = st.checkbox(" ", value=is_selected, key=checkbox_key, label_visibility="collapsed")
                if is_checked != is_selected:
                    if is_checked:
                        st.session_state.selected_products.add(nm_id)
                    else:
                        st.session_state.selected_products.discard(nm_id)
                    st.rerun()
            
            with col_photo:
                if p['photo_url']:
                    st.image(p['photo_url'], width=50)
                else:
                    st.markdown("📷")
            
            with col_info:
                title = p['title'][:40] + "..." if len(p['title']) > 40 else p['title']
                st.markdown(f"**{title}**")
                st.caption(f"Арт. {p['vendorCode']} | WB: {nm_id}")
            
            with col_price:
                price_key = f"price_{nm_id}"
                current_price = edit_data.get('price', p['price']) or 1
                if current_price < 1:
                    current_price = 1
                new_price = st.number_input(
                    " ",
                    min_value=1,
                    value=int(current_price),
                    key=price_key,
                    label_visibility="collapsed"
                )
            
            with col_discount:
                # Рассчитываем скидку автоматически
                if new_price > 0:
                    current_discounted = edit_data.get('discountedPrice', p['discountedPrice'])
                    discount_pct = int((1 - current_discounted / new_price) * 100) if current_discounted < new_price else 0
                else:
                    discount_pct = 0
                st.markdown(f"<div style='text-align: center; padding-top: 10px;'>{discount_pct}%</div>", unsafe_allow_html=True)
            
            with col_discounted:
                discounted_key = f"discounted_{nm_id}"
                current_discounted = edit_data.get('discountedPrice', p['discountedPrice']) or 1
                if current_discounted < 1:
                    current_discounted = 1
                new_discounted = st.number_input(
                    " ",
                    min_value=1,
                    value=int(current_discounted),
                    key=discounted_key,
                    label_visibility="collapsed"
                )
            
            # Сохраняем изменения
            st.session_state.price_edit_data[nm_id] = {
                'price': new_price,
                'discountedPrice': new_discounted,
                'discount': int((1 - new_discounted / new_price) * 100) if new_price > 0 and new_discounted < new_price else 0
            }
        
        # Кнопки действий снизу
        st.markdown("---")
        col_bottom1, col_bottom2, col_bottom3 = st.columns([1, 2, 1])
        
        with col_bottom1:
            if st.button("✓ Выбрать все", use_container_width=True):
                for p in all_products:
                    st.session_state.selected_products.add(p['nmID'])
                st.rerun()
        
        with col_bottom2:
            # Пустая колонка - кнопка отправки перенесена вверх
            pass
        
        with col_bottom3:
            if st.button("✗ Очистить выбор", use_container_width=True):
                st.session_state.selected_products = set()
                st.rerun()

elif page == "🤖 Автоцены":
    st.markdown("<div class='main-header'>🤖 Автоматическое ценообразование</div>", unsafe_allow_html=True)

    from pricing_strategy import (
        PricingEngine, StockStrategy, ConversionStrategy,
        TurnoverStrategy, MarginStrategy, SeasonStrategy, SeasonPeriod,
    )
    from price_history import PriceHistoryDB
    from scheduler import PriceScheduler

    agent = st.session_state.agent

    # Инициализируем PriceHistoryDB один раз
    if st.session_state.ap_history_db is None:
        st.session_state.ap_history_db = PriceHistoryDB()
    db: PriceHistoryDB = st.session_state.ap_history_db

    tab_strat, tab_sched, tab_hist = st.tabs(
        ["⚙️ Стратегии", "🕐 Расписание", "📋 История изменений"]
    )

    # ------------------------------------------------------------------ #
    #  TAB 1 — СТРАТЕГИИ                                                   #
    # ------------------------------------------------------------------ #
    with tab_strat:
        st.markdown("### Настройка стратегий")
        st.caption("Включите нужные стратегии, задайте параметры и запустите расчёт.")

        # --- StockStrategy ---
        with st.expander("📦 По остаткам (StockStrategy)", expanded=True):
            use_stock = st.checkbox("Включить", value=True, key="strat_stock_on")
            c1, c2, c3, c4 = st.columns(4)
            stock_low_thr  = c1.number_input("Мало шт (порог)",    min_value=1,   value=10,   key="stk_low_thr")
            stock_low_mul  = c2.number_input("Наценка %",          min_value=1,   value=10,   key="stk_low_mul")
            stock_high_thr = c3.number_input("Много шт (порог)",   min_value=10,  value=150,  key="stk_high_thr")
            stock_high_dis = c4.number_input("Скидка % (при много)", min_value=1, value=5,    key="stk_high_dis")

        # --- TurnoverStrategy ---
        with st.expander("🔄 По оборачиваемости (TurnoverStrategy)", expanded=True):
            use_turnover = st.checkbox("Включить", value=True, key="strat_turnover_on")
            st.caption("Оборачиваемость = остаток ÷ заказов/день. Показывает, на сколько дней хватит запаса.")
            c1, c2, c3, c4 = st.columns(4)
            turn_under_days = c1.number_input("Дефицит (дней запаса <)",  min_value=1, value=7,  key="turn_under")
            turn_markup     = c2.number_input("Наценка при дефиците %",   min_value=1, value=10, key="turn_markup")
            turn_over_days  = c3.number_input("Затоваривание (дней запаса >)", min_value=10, value=60, key="turn_over")
            turn_discount   = c4.number_input("Скидка при затоваривании %", min_value=1, value=7, key="turn_discount")

        # --- ConversionStrategy ---
        with st.expander("📉 По активности продаж (ConversionStrategy)", expanded=True):
            use_conv = st.checkbox("Включить", value=True, key="strat_conv_on")
            c1, c2, c3, c4 = st.columns(4)
            conv_no_sales = c1.number_input("Дней без продаж",  min_value=1,  value=7,   key="conv_days")
            conv_delta    = c2.number_input("Добавить скидку %", min_value=1, value=5,   key="conv_delta")
            conv_max      = c3.number_input("Макс скидка %",    min_value=5,  value=50,  key="conv_max")
            conv_fast_thr = c4.number_input("Быстрые продажи (заказов/день)", min_value=1, value=5, key="conv_fast")

        # --- MarginStrategy ---
        with st.expander("💹 По марже (MarginStrategy)"):
            use_margin = st.checkbox("Включить", value=False, key="strat_margin_on")
            st.caption("Введите себестоимость для каждого артикула через запятую: `nmID:цена, nmID:цена`")
            cost_input = st.text_area("Себестоимость", placeholder="123456:500, 789012:300", key="margin_costs")
            c1, c2, c3 = st.columns(3)
            margin_target = c1.number_input("Целевая маржа %",  min_value=1,  value=25, key="margin_target")
            margin_comm   = c2.number_input("Комиссия WB %",    min_value=1,  value=15, key="margin_comm")
            margin_tol    = c3.number_input("Допуск отклонения %", min_value=1, value=5, key="margin_tol")

        # --- SeasonStrategy ---
        with st.expander("📅 Сезонные периоды (SeasonStrategy)"):
            use_season = st.checkbox("Включить", value=False, key="strat_season_on")
            st.caption("Периоды уже включают: Чёрную пятницу (20 нояб–5 дек) и Новый год (20 дек–5 янв).")

        st.markdown("---")
        col_dry, col_apply = st.columns(2)

        def _build_strategies():
            strategies = []
            if use_stock:
                strategies.append(StockStrategy(
                    low_threshold=stock_low_thr,
                    low_markup=stock_low_mul / 100,
                    high_threshold=stock_high_thr,
                    high_discount=stock_high_dis,
                ))
            if use_turnover:
                strategies.append(TurnoverStrategy(
                    understock_days=turn_under_days,
                    markup=turn_markup / 100,
                    overstock_days=turn_over_days,
                    discount_delta=turn_discount,
                ))
            if use_conv:
                strategies.append(ConversionStrategy(
                    no_sales_days=conv_no_sales,
                    discount_delta=conv_delta,
                    max_discount=conv_max,
                    fast_threshold=float(conv_fast_thr),
                ))
            if use_margin and cost_input.strip():
                try:
                    costs = {}
                    for pair in cost_input.split(","):
                        nm, cost = pair.strip().split(":")
                        costs[int(nm.strip())] = float(cost.strip())
                    strategies.append(MarginStrategy(
                        cost_prices=costs,
                        target_margin=margin_target / 100,
                        wb_commission=margin_comm / 100,
                        tolerance=margin_tol / 100,
                    ))
                except Exception:
                    st.warning("Неверный формат себестоимости. Пример: `123456:500, 789012:300`")
            if use_season:
                strategies.append(SeasonStrategy(periods=[
                    SeasonPeriod("Чёрная пятница",       "11-20", "12-05", discount_add=10),
                    SeasonPeriod("Новогодняя распродажа", "12-20", "01-05", discount_add=15),
                ]))
            return strategies

        with col_dry:
            if st.button("🔍 Рассчитать (dry-run)", use_container_width=True, type="secondary"):
                strategies = _build_strategies()
                if not strategies:
                    st.warning("Включите хотя бы одну стратегию.")
                else:
                    with st.spinner("Анализируем товары..."):
                        try:
                            engine = PricingEngine(
                                agent.products, agent.analytics, agent.inventory,
                                strategies=strategies,
                            )
                            actions = engine.run(dry_run=True)
                            st.session_state.ap_last_actions = actions
                            if actions:
                                st.success(f"Найдено {len(actions)} товаров для переоценки.")
                            else:
                                st.info("Все цены оптимальны — изменений не требуется.")
                        except Exception as e:
                            st.error(f"Ошибка: {e}")

        with col_apply:
            if st.button("✅ Применить изменения", use_container_width=True, type="primary"):
                strategies = _build_strategies()
                if not strategies:
                    st.warning("Включите хотя бы одну стратегию.")
                else:
                    with st.spinner("Применяем новые цены..."):
                        try:
                            engine = PricingEngine(
                                agent.products, agent.analytics, agent.inventory,
                                strategies=strategies,
                            )
                            actions = engine.run(dry_run=False)
                            st.session_state.ap_last_actions = actions
                            db.record_many(actions)
                            applied = sum(1 for a in actions if a.applied)
                            st.success(f"Применено {applied} из {len(actions)} изменений. Записано в историю.")
                        except Exception as e:
                            st.error(f"Ошибка: {e}")

        # Таблица результатов
        if st.session_state.ap_last_actions:
            st.markdown("#### Результаты расчёта")
            rows = [
                {
                    "nmID":        a.nm_id,
                    "Артикул":     a.vendor_code,
                    "Название":    a.title,
                    "Цена было":   int(a.old_price),
                    "Цена стало":  int(a.new_price),
                    "Скидка было": f"{a.old_discount}%",
                    "Скидка стало": f"{a.new_discount}%",
                    "Стратегия":   a.strategy_name,
                    "Причина":     a.reason,
                    "Применено":   "✅" if a.applied else "📋",
                }
                for a in st.session_state.ap_last_actions
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ #
    #  TAB 2 — РАСПИСАНИЕ                                                  #
    # ------------------------------------------------------------------ #
    with tab_sched:
        st.markdown("### Автоматический запуск")
        st.caption("Планировщик работает в фоне пока открыт браузер с дашбордом.")

        sched: PriceScheduler = st.session_state.ap_scheduler

        # Статус
        if sched and sched._running:
            status = sched.get_status()
            st.success(f"**Статус: запущен** | Следующий прогон: `{status['next_run']}`")
            st.caption(
                f"Последний запуск: {status['last_run']}  |  "
                f"Всего прогонов: {status['total_runs']}  |  "
                f"Стратегии: {', '.join(status['strategies'])}"
            )
        else:
            st.warning("Планировщик остановлен.")

        st.markdown("---")
        st.markdown("#### Настройки")

        mode = st.radio("Режим", ["Интервал (каждые N часов)", "Ежедневно в заданное время"],
                        horizontal=True, key="sched_mode")

        c1, c2, c3 = st.columns(3)
        with c1:
            sched_hours = st.number_input("Каждые часов", min_value=1, max_value=24, value=4, key="sched_hours")
        with c2:
            sched_cron_h = st.number_input("Час (0–23)",   min_value=0, max_value=23, value=2,  key="sched_cron_h")
            sched_cron_m = st.number_input("Минута (0–59)", min_value=0, max_value=59, value=0, key="sched_cron_m")
        with c3:
            sched_dry = st.checkbox("Dry-run (не применять)", value=True, key="sched_dry")
            st.caption("Снимите галочку чтобы реально менять цены.")

        col_start, col_stop, col_now = st.columns(3)

        with col_start:
            if st.button("▶ Запустить", use_container_width=True, type="primary",
                         disabled=(sched is not None and sched._running)):
                strategies = [
                    StockStrategy(),
                    ConversionStrategy(),
                    SeasonStrategy(periods=[
                        SeasonPeriod("Чёрная пятница",       "11-20", "12-05", discount_add=10),
                        SeasonPeriod("Новогодняя распродажа", "12-20", "01-05", discount_add=15),
                    ]),
                ]
                engine = PricingEngine(
                    agent.products, agent.analytics, agent.inventory,
                    strategies=strategies,
                )
                new_sched = PriceScheduler(engine, dry_run=sched_dry)
                if mode == "Интервал (каждые N часов)":
                    new_sched.add_interval(hours=sched_hours)
                else:
                    new_sched.add_cron(hour=sched_cron_h, minute=sched_cron_m)
                new_sched.start()
                st.session_state.ap_scheduler = new_sched
                st.success("Планировщик запущен.")
                st.rerun()

        with col_stop:
            if st.button("⏹ Остановить", use_container_width=True,
                         disabled=(sched is None or not sched._running)):
                sched.stop()
                st.session_state.ap_scheduler = None
                st.info("Планировщик остановлен.")
                st.rerun()

        with col_now:
            if st.button("⚡ Запустить сейчас", use_container_width=True):
                strategies = [StockStrategy(), ConversionStrategy()]
                engine = PricingEngine(
                    agent.products, agent.analytics, agent.inventory,
                    strategies=strategies,
                )
                one_shot = PriceScheduler(engine, dry_run=sched_dry)
                with st.spinner("Выполняем переоценку..."):
                    result = one_shot.run_now()
                db.record_many(result.actions)
                st.session_state.ap_last_actions = result.actions
                if result.error:
                    st.error(f"Ошибка: {result.error}")
                else:
                    st.success(str(result))

        # История прогонов планировщика
        if sched:
            history = sched.get_history(10)
            if history:
                st.markdown("#### Последние прогоны")
                run_rows = [
                    {
                        "Время":       r.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "Режим":       "dry-run" if r.dry_run else "applied",
                        "Изменений":   r.actions_count,
                        "Применено":   r.applied_count,
                        "Длит. (с)":   f"{r.duration_sec:.1f}",
                        "Ошибка":      r.error or "",
                    }
                    for r in reversed(history)
                ]
                st.dataframe(pd.DataFrame(run_rows), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ #
    #  TAB 3 — ИСТОРИЯ                                                     #
    # ------------------------------------------------------------------ #
    with tab_hist:
        st.markdown("### Журнал изменений цен")

        # Статистика
        stats = db.stats()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Всего записей",    stats["total"])
        m2.metric("Применено",        stats["applied"])
        m3.metric("Откатов",          stats["rolled_back"])
        m4.metric("Уникальных товаров", stats["unique_products"])

        if stats["by_strategy"]:
            st.caption("По стратегиям: " + "  |  ".join(
                f"{k}: **{v}**" for k, v in stats["by_strategy"].items()
            ))

        st.markdown("---")

        # Фильтры
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            hist_date_from = st.date_input("С даты", value=datetime.now() - timedelta(days=30), key="hist_from")
        with fc2:
            hist_date_to = st.date_input("По дату", value=datetime.now(), key="hist_to")
        with fc3:
            hist_applied = st.checkbox("Только применённые", value=False, key="hist_applied")

        if st.button("🔄 Загрузить историю", key="hist_load"):
            records = db.get_all(
                date_from=str(hist_date_from),
                date_to=str(hist_date_to),
                applied_only=hist_applied,
                limit=500,
            )
            if records:
                df_hist = pd.DataFrame(records)[[
                    "created_at", "nm_id", "vendor_code", "title",
                    "old_price", "new_price", "old_discount", "new_discount",
                    "strategy_name", "reason", "applied", "rolled_back",
                ]]
                df_hist.columns = [
                    "Время", "nmID", "Артикул", "Название",
                    "Цена было", "Цена стало", "Скидка было", "Скидка стало",
                    "Стратегия", "Причина", "Применено", "Откат",
                ]
                df_hist["Применено"] = df_hist["Применено"].map({1: "✅", 0: "📋"})
                df_hist["Откат"]     = df_hist["Откат"].map({1: "↩️", 0: ""})
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.info("Нет записей за выбранный период.")

        st.markdown("---")
        st.markdown("#### Откат изменений")

        rc1, rc2 = st.columns(2)
        with rc1:
            rollback_nm = st.number_input("Откатить по nmID:", min_value=1, value=1, key="rb_nm")
            if st.button("↩️ Откатить последнее изменение", key="rb_one"):
                with st.spinner("Откат..."):
                    ok = db.rollback_last(nm_id=rollback_nm, products_mgr=agent.products)
                if ok:
                    st.success(f"Цена nmID={rollback_nm} откатана.")
                else:
                    st.warning(f"Нет применённых изменений для nmID={rollback_nm}.")

        with rc2:
            rollback_hours = st.number_input("Откатить все за последние часов:", min_value=1, value=24, key="rb_hours")
            if st.button("↩️ Откатить все за период", type="secondary", key="rb_all"):
                with st.spinner(f"Откат всех изменений за {rollback_hours} ч..."):
                    results = db.rollback_since(hours=rollback_hours, products_mgr=agent.products)
                success = sum(1 for v in results.values() if v)
                if results:
                    st.success(f"Откатано {success} из {len(results)} товаров.")
                else:
                    st.info("Нет изменений для отката за этот период.")

        st.markdown("---")
        with st.expander("🗑️ Очистка старых записей"):
            purge_days = st.number_input("Удалить записи старше дней:", min_value=7, value=90, key="purge_days")
            if st.button("Удалить", type="secondary", key="purge_btn"):
                deleted = db.purge_old(days=purge_days)
                st.success(f"Удалено {deleted} записей.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Wildberries AI Agent v1.0**")
st.sidebar.markdown("Создано для автоматизации магазина WB")
