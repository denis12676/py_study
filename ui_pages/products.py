import streamlit as st
import pandas as pd

def render_products_page():
    """Отрисовка страницы товаров"""
    st.markdown("<div class='main-header'>📦 Управление товарами</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Каталог", "Поиск", "Цены"])
    
    with tab1:
        if st.button("🔄 Загрузить каталог", type="primary", key="load_catalog"):
            with st.spinner("Загрузка товаров..."):
                products = st.session_state.agent.products.get_all_products(limit=100)
                if products:
                    st.success(f"Загружено {len(products)} товаров")
                    df_data = []
                    for p in products:
                        sizes = p.get('sizes', [])
                        price = sizes[0].get('price', 0) if sizes else 0
                        df_data.append({
                            'Артикул': p.get('nmID'),
                            'Название': p.get('title', '')[:50],
                            'Артикул продавца': p.get('vendorCode', ''),
                            'Бренд': p.get('brand', ''),
                            'Цена': price,
                            'Предмет': p.get('subjectName', '')
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True)
    
    with tab2:
        search_query = st.text_input("Поиск товара:", placeholder="Введите артикул или название", key="prod_search")
        if st.button("🔍 Искать", key="prod_search_btn"):
            if search_query:
                with st.spinner("Поиск..."):
                    results = st.session_state.agent.products.search_products(search_query)
                    if results:
                        st.json(results[:5])
                    else:
                        st.info("Ничего не найдено")
    
    with tab3:
        col1, col2, col3 = st.columns(3)
        nm_id = col1.number_input("Артикул (nmID):", min_value=1, value=1, key="price_nm_id")
        new_price = col2.number_input("Новая цена:", min_value=1, value=1000, key="price_val")
        discount = col3.number_input("Скидка (%):", min_value=0, max_value=95, value=0, key="price_disc")
        
        if st.button("💾 Обновить цену", type="primary", key="update_price_btn"):
            with st.spinner("Обновление..."):
                result = st.session_state.agent.products.update_price(nm_id, new_price, discount)
                st.success("Цена обновлена!")
                st.json(result)
