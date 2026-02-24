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

# Page configuration
st.set_page_config(
    page_title="Wildberries AI Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #7B68EE;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .status-online {
        color: #00C851;
        font-weight: bold;
    }
    .status-offline {
        color: #ff4444;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3rem;
        font-weight: bold;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        font-size: 14px;
        line-height: 1.5;
    }
    .chat-user {
        background-color: #E3F2FD;
        margin-left: 20%;
        color: #333;
    }
    .chat-bot {
        background-color: #F3E5F5;
        margin-right: 20%;
        color: #333;
    }
    .chat-bot pre {
        background-color: #f5f5f5;
        padding: 0.5rem;
        border-radius: 5px;
        overflow-x: auto;
        font-size: 12px;
    }
    .chat-bot code {
        background-color: #f5f5f5;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'products_data' not in st.session_state:
    st.session_state.products_data = None
if 'sales_data' not in st.session_state:
    st.session_state.sales_data = None

# Sidebar
st.sidebar.markdown("## 🛍️ WB AI Agent")
st.sidebar.markdown("---")

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
            st.sidebar.markdown("<div style='color: green;'>✓ Токен будет использован автоматически</div>", unsafe_allow_html=True)
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
    
    if st.sidebar.button("🚀 Подключиться", type="primary"):
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
    
    st.sidebar.markdown("---")
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
    
    st.sidebar.markdown("---")

# Main navigation
page = st.sidebar.radio(
    "📍 Навигация",
    ["🏠 Главная", "💬 AI Чат", "📦 Товары", "📋 Остатки", "📊 Аналитика", "📢 Реклама"]
)

# Main content
if page == "🏠 Главная":
    st.markdown("<div class='main-header'>📊 Дашборд Wildberries</div>", unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        # Get revenue data
        revenue = st.session_state.agent.analytics.calculate_revenue(days=30)
        
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{revenue['total_revenue']:,.0f} ₽</div>
                <div class='metric-label'>Выручка (30 дней)</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{revenue['total_sales']}</div>
                <div class='metric-label'>Продаж</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{revenue['average_check']:,.0f} ₽</div>
                <div class='metric-label'>Средний чек</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Get products count
        products = st.session_state.agent.products.get_all_products(limit=1)
        with col4:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{len(products) if products else '...'}+</div>
                <div class='metric-label'>Товаров</div>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {str(e)}")
        st.info("💡 Попробуйте обновить страницу или проверить API токен. Если ошибка повторяется - возможно, проблемы с серверами WB.")
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### ⚡ Быстрые действия")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📦 Показать товары", use_container_width=True):
            st.session_state.quick_action = "products"
    
    with col2:
        if st.button("💰 Выручка за 30 дней", use_container_width=True):
            st.session_state.quick_action = "revenue"
    
    with col3:
        if st.button("🔥 Топ товаров", use_container_width=True):
            st.session_state.quick_action = "top"
    
    with col4:
        if st.button("📢 Рекламные кампании", use_container_width=True):
            st.session_state.quick_action = "campaigns"
    
    # Вторая строка быстрых действий
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Еженедельный отчет", use_container_width=True):
            st.session_state.quick_action = "weekly"
    
    # Execute quick action
    if 'quick_action' in st.session_state:
        with st.spinner("Загрузка..."):
            try:
                if st.session_state.quick_action == "products":
                    products = st.session_state.agent.products.get_all_products(limit=100)
                    if products:
                        st.success(f"Загружено {len(products)} товаров")
                        # Convert to DataFrame with safe data extraction
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
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Нет данных о товарах")
                        
                elif st.session_state.quick_action == "revenue":
                    revenue = st.session_state.agent.analytics.calculate_revenue(days=30)
                    
                    # Красивое отображение вместо JSON
                    st.success(f"📊 Отчет за {revenue['period_days']} дней")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("💰 Выручка", f"{revenue['total_revenue']:,.0f} ₽")
                    with col2:
                        st.metric("📦 Продаж", f"{revenue['total_sales']}")
                    with col3:
                        st.metric("📈 Средний чек", f"{revenue['average_check']:,.0f} ₽")
                    
                    # Красивое отображение суммы
                    st.markdown(f"### Итого: **{revenue['total_revenue']:,.2f} ₽**")
                    st.markdown(f"Всего продаж: **{revenue['total_sales']}** | Средний чек: **{revenue['average_check']:,.2f} ₽**")
                    
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
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Нет рекламных кампаний")
                
                elif st.session_state.quick_action == "weekly":
                    report = st.session_state.agent.analytics.get_weekly_sales_report()
                    if report and not report.get('error'):
                        st.success(f"Отчет за неделю: {report['week_start']} - {report['week_end']}")
                        
                        # Метрики
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Выручка", f"{report['total_revenue']:,.0f} ₽")
                        col2.metric("Продаж", report['total_sales'])
                        col3.metric("Возвратов", report['total_returns'])
                        col4.metric("Средний чек", f"{report['average_check']:,.0f} ₽")
                        
                        # Дневная разбивка
                        if report.get('daily_breakdown'):
                            st.markdown("### 📈 По дням")
                            df_daily = pd.DataFrame(report['daily_breakdown'])
                            st.dataframe(df_daily, use_container_width=True)
                        
                        # Топ товары
                        if report.get('top_products'):
                            st.markdown("### 🏆 Топ товары")
                            df_products = pd.DataFrame(report['top_products'][:10])
                            st.dataframe(df_products, use_container_width=True)
                        
                        # Кнопка экспорта
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
                if "429" in error_msg or "Слишком много" in error_msg or "Rate limit" in error_msg:
                    st.error("⚠️ Превышен лимит запросов к API Wildberries")
                    st.info("💡 Пожалуйста, подождите 1-2 минуты и попробуйте снова. Лимит: 1 запрос в минуту для статистики.")
                else:
                    st.error(f"❌ Ошибка: {error_msg}")
        
        del st.session_state.quick_action

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
                    st.dataframe(df, use_container_width=True)
                    
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
    
    tab_fbs, tab_fbo = st.tabs(["📦 FBS (склад продавца)", "🏭 FBO (склад WB)"])
    
    with tab_fbs:
        st.markdown("### 📦 Остатки на складе продавца (FBS)")
        
        if st.button("🔄 Загрузить склады", type="primary", key="fbs_load_warehouses"):
            with st.spinner("Загрузка складов..."):
                try:
                    warehouses = st.session_state.agent.products.get_warehouses()
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
                        stocks = st.session_state.agent.products.get_stocks(warehouse_id)
                        st.session_state.fbs_stocks = stocks
                        
                        if stocks:
                            st.success(f"Загружено {len(stocks)} позиций")
                            
                            df_data = []
                            for s in stocks:
                                df_data.append({
                                    'Баркод': s.get('sku', ''),
                                    'Артикул': s.get('nmId', ''),
                                    'Остаток': s.get('amount', 0),
                                    'В пути': s.get('inTransit', 0)
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(df, use_container_width=True)
                            
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
        st.markdown("*Данные по остаткам на всех складах Wildberries*")
        
        if st.button("🔄 Загрузить остатки FBO", type="primary", key="fbo_load"):
            with st.spinner("Загрузка остатков FBO..."):
                try:
                    result = st.session_state.agent.products.get_fbo_stocks()
                    st.session_state.fbo_stocks = result
                    
                    regions = result.get('regions', [])
                    
                    if regions:
                        st.success(f"Загружено {len(regions)} регионов со складами")
                        
                        # Подсчет общих метрик
                        total_stock_count = 0
                        total_stock_sum = 0
                        total_offices = 0
                        
                        for region in regions:
                            metrics = region.get('metrics', {})
                            total_stock_count += metrics.get('stockCount', 0)
                            total_stock_sum += metrics.get('stockSum', 0)
                            total_offices += len(region.get('offices', []))
                        
                        # Метрики
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Всего товаров", f"{total_stock_count:,}")
                        with col2:
                            st.metric("Сумма остатков", f"{total_stock_sum:,} ₽")
                        with col3:
                            st.metric("Количество складов", total_offices)
                        
                        # Таблица по регионам
                        df_regions = []
                        for region in regions:
                            metrics = region.get('metrics', {})
                            df_regions.append({
                                'Регион': region.get('regionName', ''),
                                'Товаров': metrics.get('stockCount', 0),
                                'Сумма': f"{metrics.get('stockSum', 0):,} ₽",
                                'Складов': len(region.get('offices', []))
                            })
                        
                        st.markdown("#### 📊 По регионам")
                        df = pd.DataFrame(df_regions)
                        st.dataframe(df, use_container_width=True)
                        
                        # Детализация по складам
                        st.markdown("#### 📋 Детализация по складам")
                        all_offices = []
                        for region in regions:
                            for office in region.get('offices', []):
                                metrics = office.get('metrics', {})
                                all_offices.append({
                                    'Регион': region.get('regionName', ''),
                                    'Склад': office.get('officeName', ''),
                                    'ID склада': office.get('officeID', ''),
                                    'Товаров': metrics.get('stockCount', 0),
                                    'Сумма': f"{metrics.get('stockSum', 0):,} ₽"
                                })
                        
                        if all_offices:
                            df_offices = pd.DataFrame(all_offices)
                            st.dataframe(df_offices, use_container_width=True)
                        
                        # Скачать CSV
                        csv_data = []
                        for region in regions:
                            for office in region.get('offices', []):
                                metrics = office.get('metrics', {})
                                csv_data.append({
                                    'region': region.get('regionName', ''),
                                    'office_id': office.get('officeID', ''),
                                    'office_name': office.get('officeName', ''),
                                    'stock_count': metrics.get('stockCount', 0),
                                    'stock_sum': metrics.get('stockSum', 0)
                                })
                        
                        if csv_data:
                            df_csv = pd.DataFrame(csv_data)
                            csv = df_csv.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "📥 Скачать CSV",
                                csv,
                                "fbo_stocks_by_warehouse.csv",
                                "text/csv",
                                key="fbo_download"
                            )
                    else:
                        st.info("Нет данных о остатках FBO. Возможно, у вас нет товаров на складах WB.")
                except Exception as e:
                    st.error(f"Ошибка загрузки: {e}")
                    import traceback
                    st.code(traceback.format_exc())

elif page == "📊 Аналитика":
    st.markdown("<div class='main-header'>📊 Аналитика продаж</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        period = st.selectbox("Период:", ["7 дней", "30 дней", "90 дней"])
        days = {"7 дней": 7, "30 дней": 30, "90 дней": 90}[period]
    
    with col2:
        detail_level = st.selectbox("Детализация:", ["Простая", "Детальная (с вычетами)"])
    
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
                st.dataframe(df_details, use_container_width=True, hide_index=True)
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
                st.dataframe(df, use_container_width=True)
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

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Wildberries AI Agent v1.0**")
st.sidebar.markdown("Создано для автоматизации магазина WB")
