import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory_page():
    """Отрисовка страницы остатков"""
    st.markdown("<div class='main-header'>📋 Остатки товаров</div>", unsafe_allow_html=True)
    
    tab_fbs, tab_fbo, tab_summary = st.tabs(["FBS (склад продавца)", "FBO (склад WB)", "Сводка"])
    
    with tab_fbs:
        if st.button("🔄 Загрузить склады FBS", type="primary"):
            warehouses = st.session_state.agent.inventory.get_warehouses()
            st.session_state.fbs_warehouses = warehouses
        
        if 'fbs_warehouses' in st.session_state and st.session_state.fbs_warehouses:
            warehouse_options = {w.get('name', f"Склад {w.get('id')}"): w.get('id') for w in st.session_state.fbs_warehouses}
            selected_warehouse = st.selectbox("Выберите склад:", options=list(warehouse_options.keys()))
            
            if st.button("📥 Загрузить остатки FBS"):
                stocks = st.session_state.agent.inventory.get_stocks(warehouse_options[selected_warehouse])
                st.dataframe(pd.DataFrame(stocks), use_container_width=True)
    
    with tab_fbo:
        if st.button("📦 Загрузить остатки FBO", type="primary"):
            with st.spinner("Загрузка..."):
                stocks = st.session_state.agent.inventory.get_fbo_stocks()
                st.dataframe(pd.DataFrame(stocks), use_container_width=True)

    with tab_summary:
        if st.button("Собрать сводную таблицу", type="primary"):
            # Упрощенная логика для примера рефакторинга
            st.info("Сборка сводной таблицы...")
