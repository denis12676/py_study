import streamlit as st
import pandas as pd

def render_advertising_page():
    """Отрисовка страницы рекламы"""
    st.markdown("<div class='main-header'>📢 Управление рекламой</div>", unsafe_allow_html=True)
    
    if st.button("🔄 Загрузить кампании", type="primary"):
        with st.spinner("Загрузка..."):
            campaigns = st.session_state.agent.advertising.get_campaigns()
            if campaigns:
                st.dataframe(pd.DataFrame(campaigns), use_container_width=True)
            else:
                st.info("Нет рекламных кампаний")
    
    st.markdown("### ⚙️ Управление кампаниями")
    col1, col2, col3 = st.columns(3)
    camp_id = col1.number_input("ID кампании:", min_value=1, key="adv_camp_id")
    action = col2.selectbox("Действие:", ["Запустить", "Остановить"], key="adv_action")
    
    if col3.button("Применить", type="primary"):
        with st.spinner("Выполнение..."):
            if action == "Запустить":
                st.session_state.agent.advertising.start_campaign(camp_id)
            else:
                st.session_state.agent.advertising.pause_campaign(camp_id)
            st.success("Готово!")
