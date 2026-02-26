import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render_home_page():
    """Отрисовка главной страницы дашборда"""
    # Modern header with top bar
    col_title, col_period = st.columns([3, 1])
    with col_title:
        st.markdown("<div class='main-header'>📊 Сводка по финансам</div>", unsafe_allow_html=True)
    with col_period:
        period = st.selectbox("Период:", ["7 дней", "30 дней", "90 дней"], index=1, key="home_period_select")
    
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
            if st.button("📦 Показать товары", use_container_width=True, key="qa_products"):
                st.session_state.quick_action = "products"
        
        with col2:
            if st.button("💰 Выручка", use_container_width=True, key="qa_revenue"):
                st.session_state.quick_action = "revenue"
        
        with col3:
            if st.button("🔥 Топ товаров", use_container_width=True, key="qa_top"):
                st.session_state.quick_action = "top"
        
        with col4:
            if st.button("📢 Реклама", use_container_width=True, key="qa_ads"):
                st.session_state.quick_action = "campaigns"
        
        # Second row
        st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Отчет за неделю", use_container_width=True, key="qa_weekly"):
                st.session_state.quick_action = "weekly"
        
        # Execute quick action
        if 'quick_action' in st.session_state:
            _render_quick_action()
    
    with tab_ozon:
        st.info("Интеграция с Ozon будет доступна в следующей версии.")

def _render_quick_action():
    """Вспомогательная функция для отрисовки результатов быстрых действий"""
    with st.spinner("Загрузка..."):
        try:
            if st.session_state.quick_action == "products":
                products = st.session_state.agent.products.get_all_products(limit=100)
                if products:
                    st.success(f"Загружено {len(products)} товаров")
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
                st.success(f"📊 Отчет за {revenue['period_days']} дней")
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Выручка", f"{revenue['total_revenue']:,.0f} ₽")
                col2.metric("📦 Продаж", f"{revenue['total_sales']}")
                col3.metric("📈 Средний чек", f"{revenue['average_check']:,.0f} ₽")
                
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
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Выручка", f"{report['total_revenue']:,.0f} ₽")
                    col2.metric("Продаж", report['total_sales'])
                    col3.metric("Возвратов", report['total_returns'])
                    col4.metric("Средний чек", f"{report['average_check']:,.0f} ₽")
                else:
                    st.info("Нет данных за прошлую неделю")
                    
        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
    
    del st.session_state.quick_action
