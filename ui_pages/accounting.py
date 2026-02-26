import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "wb_cache.db"

def render_accounting_page():
    st.markdown("<div class='main-header'>🧾 Учетная система (P&L)</div>", unsafe_allow_html=True)
    
    user_id = st.session_state.user['id']
    tab_costs, tab_expenses, tab_summary = st.tabs(["💰 Себестоимость", "📉 Прочие расходы", "📊 Чистая прибыль"])
    
    with tab_costs:
        st.subheader("Настройка себестоимости")
        if st.button("📥 Синхронизировать товары из WB"):
            with st.spinner("Загрузка..."):
                products = st.session_state.agent.products.get_all_products(limit=500)
                with sqlite3.connect(DB_PATH) as conn:
                    for p in products:
                        p_dict = p.model_dump()
                        conn.execute(
                            "INSERT OR IGNORE INTO product_costs (nm_id, vendor_code, user_id) VALUES (?, ?, ?)",
                            (p_dict['nm_id'], p_dict['vendor_code'], user_id)
                        )
                st.success("Каталог обновлен!")

        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT nm_id, vendor_code, purchase_price, tax_percent FROM product_costs WHERE user_id = ?", conn, params=(user_id,))
        
        if not df.empty:
            edited_df = st.data_editor(df, key="costs_editor", hide_index=True, use_container_width=True)
            if st.button("💾 Сохранить цены закупки"):
                with sqlite3.connect(DB_PATH) as conn:
                    for _, row in edited_df.iterrows():
                        conn.execute(
                            "UPDATE product_costs SET purchase_price = ?, tax_percent = ? WHERE nm_id = ? AND user_id = ?",
                            (row['purchase_price'], row['tax_percent'], row['nm_id'], user_id)
                        )
                st.success("Сохранено!")

    with tab_expenses:
        st.subheader("Операционные расходы")
        col1, col2, col3 = st.columns(3)
        cat = col1.text_input("На что потратили:")
        amount = col2.number_input("Сумма (₽):", min_value=0.0)
        if col3.button("➕ Добавить"):
            if cat and amount > 0:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("INSERT INTO expenses (category, amount, date, user_id) VALUES (?, ?, ?, ?)", 
                                (cat, amount, pd.Timestamp.now().strftime("%Y-%m-%d"), user_id))
                st.rerun()
        
        with sqlite3.connect(DB_PATH) as conn:
            exp_df = pd.read_sql_query("SELECT category, amount, date FROM expenses WHERE user_id = ? ORDER BY date DESC", conn, params=(user_id,))
            if not exp_df.empty:
                st.table(exp_df)

    with tab_summary:
        _render_detailed_pnl(user_id)

def _render_detailed_pnl(user_id):
    st.subheader("Детальный расчет прибыли за 30 дней")
    
    if st.button("🔄 Сначала обновить финансовые отчеты из WB"):
        with st.spinner("Загрузка отчетов из API (может занять время)..."):
            import asyncio
            asyncio.run(st.session_state.agent.analytics.sync_reports_to_db(user_id))
            st.success("Отчеты синхронизированы!")
            st.rerun()

    data = st.session_state.agent.analytics.get_full_pnl_data(user_id)
    
    if data['gross_revenue'] == 0:
        st.warning("Нет данных в финансовом отчете. Пожалуйста, нажмите кнопку обновления выше.")
        return

    # Основные метрики
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Выручка", f"{data['gross_revenue']:,.0f} ₽")
    c2.metric("📉 Расходы", f"-{data['gross_revenue'] - data['net_profit']:,.0f} ₽")
    c3.metric("📈 Чистая прибыль", f"{data['net_profit']:,.0f} ₽")
    roi = (data['net_profit'] / data['total_cogs'] * 100) if data['total_cogs'] > 0 else 0
    c4.metric("📊 ROI", f"{roi:.1f}%")

    st.markdown("---")
    
    # Визуализация структуры
    col_chart, col_table = st.columns([1, 1])
    
    with col_chart:
        # Готовим данные для круговой диаграммы
        costs_breakdown = {
            'Маржа (Чистая прибыль)': max(0, data['net_profit']),
            'Себестоимость (COGS)': data['total_cogs'],
            'Комиссия WB': data['total_commission'],
            'Логистика WB': data['total_logistics'],
            'Налоги': data['total_taxes'],
            'Хранение/Штрафы': data['total_storage'] + data['total_penalties'],
            'Прочие расходы': data['other_expenses']
        }
        fig = px.pie(
            names=list(costs_breakdown.keys()), 
            values=list(costs_breakdown.values()),
            title="Структура выручки",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.write("**Детализация:**")
        stats_df = pd.DataFrame([
            {"Показатель": "Выручка (Грязная)", "Сумма": f"{data['gross_revenue']:,.2f} ₽"},
            {"Показатель": "Выплата от WB (за вычетом комиссии)", "Сумма": f"{data['net_payout']:,.2f} ₽"},
            {"Показатель": "Логистика", "Сумма": f"-{data['total_logistics']:,.2f} ₽"},
            {"Показатель": "Себестоимость закупки", "Сумма": f"-{data['total_cogs']:,.2f} ₽"},
            {"Показатель": "Налоги (расчетные)", "Сумма": f"-{data['total_taxes']:,.2f} ₽"},
            {"Показатель": "Прочие расходы (аренда и т.д.)", "Сумма": f"-{data['other_expenses']:,.2f} ₽"},
            {"Показатель": "ИТОГО ЧИСТАЯ ПРИБЫЛЬ", "Сумма": f"{data['net_profit']:,.2f} ₽"},
        ])
        st.table(stats_df.set_index("Показатель"))
