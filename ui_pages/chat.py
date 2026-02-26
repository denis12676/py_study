import streamlit as st
import json

def render_chat_page():
    """Отрисовка страницы AI чата"""
    st.markdown("<div class='main-header'>💬 AI Ассистент Wildberries</div>", unsafe_allow_html=True)
    
    # Chat history
    for message in st.session_state.chat_history:
        role = "Вы" if message['role'] == 'user' else "AI"
        css_class = "chat-user" if message['role'] == 'user' else "chat-bot"
        st.markdown(f"<div class='chat-message {css_class}'><b>{role}:</b> {message['content']}</div>", unsafe_allow_html=True)
    
    # Input
    user_input = st.text_input("Ваш запрос:", placeholder="Например: Покажи все товары", key="chat_input")
    
    col1, col2 = st.columns([1, 5])
    if col1.button("Отправить", type="primary"):
        if user_input:
            st.session_state.chat_history.append({'role': 'user', 'content': user_input})
            with st.spinner("AI обрабатывает запрос..."):
                try:
                    result = st.session_state.agent.execute(user_input)
                    response = _format_chat_response(result)
                    st.session_state.chat_history.append({'role': 'bot', 'content': response})
                except Exception as e:
                    st.session_state.chat_history.append({'role': 'bot', 'content': f"Ошибка: {str(e)}"})
            st.rerun()
    
    if col2.button("Очистить чат"):
        st.session_state.chat_history = []
        st.rerun()

def _format_chat_response(result):
    """Форматирование ответа для чата"""
    if isinstance(result, list):
        return f"Найдено {len(result)} записей."
    if isinstance(result, dict):
        return f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
    return str(result)
