import logging
import streamlit as st
import sys
import os
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_agent import WildberriesAIAgent
from styles import get_dark_theme_css
from logging_config import setup_logging
from auth_utils import login_user, create_user, init_db, start_session, get_user_by_session, close_session
from ui_pages.home import render_home_page
from ui_pages.analytics import render_analytics_page
from ui_pages.products import render_products_page
from ui_pages.inventory import render_inventory_page
from ui_pages.chat import render_chat_page
from ui_pages.advertising import render_advertising_page
from ui_pages.autoprices import render_autoprices_page
from ui_pages.accounting import render_accounting_page

setup_logging()
logger = logging.getLogger(__name__)

# Initialize DB tables
init_db()

DB_PATH = Path(__file__).parent / "wb_cache.db"

# --- Session State ---
def init_session_state():
    defaults = {
        'user': None,
        'agent': None,
        'current_account': None,
        'current_page': "🏠 Главная"
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# --- Auth Logic with persistence ---
def check_auth_persistence():
    """Проверка сохраненной сессии в URL"""
    if st.session_state.user is None:
        # Проверяем query params
        session_id = st.query_params.get("session")
        if session_id:
            user = get_user_by_session(session_id)
            if user:
                st.session_state.user = user
                logger.info(f"Session restored for user: {user['username']}")
                return True
    return False

def render_auth():
    st.markdown("<h1 style='text-align: center;'>🛍️ MultiMarket AI</h1>", unsafe_allow_html=True)
    
    choice = st.radio("Выберите действие:", ["Вход", "Регистрация"], horizontal=True)
    
    with st.form("auth_form"):
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Выполнить")
        
        if submit:
            if not username or not password:
                st.error("Заполните все поля")
            elif choice == "Регистрация":
                if create_user(username, password):
                    st.success("Успешная регистрация! Теперь войдите.")
                else:
                    st.error("Пользователь с таким логином уже существует")
            else:
                user = login_user(username, password)
                if user:
                    # Создаем долгоживущую сессию
                    sid = start_session(user['id'])
                    st.query_params["session"] = sid
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль")
    st.stop()

def logout():
    sid = st.query_params.get("session")
    if sid:
        close_session(sid)
    st.query_params.clear()
    st.session_state.user = None
    st.session_state.agent = None
    st.rerun()

# --- Database Helpers ---
def get_accounts():
    user_id = st.session_state.user['id']
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM accounts WHERE user_id = ? ORDER BY name", (user_id,)).fetchall()]

def add_account(name, token):
    user_id = st.session_state.user['id']
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO accounts (name, token, user_id) VALUES (?, ?, ?)", (name, token, user_id))
            return True
    except: return False

# --- Main App ---
def main():
    st.set_page_config(page_title="MultiMarket AI", page_icon="🛍️", layout="wide")
    st.markdown(get_dark_theme_css(), unsafe_allow_html=True)

    # Проверяем сохраненную сессию
    check_auth_persistence()

    if not st.session_state.user:
        render_auth()

    # Сайдбар
    st.sidebar.markdown(f"👤 **Пользователь:** {st.session_state.user['username']}")
    if st.sidebar.button("🚪 Выйти из системы"):
        logout()

    # Управление магазинами
    st.sidebar.markdown("---")
    accounts = get_accounts()
    
    if not accounts:
        st.sidebar.warning("Добавьте магазин")
    else:
        acc_names = [a['name'] for a in accounts]
        current_idx = 0
        if st.session_state.current_account:
            try: current_idx = acc_names.index(st.session_state.current_account['name'])
            except: pass
            
        selected_acc_name = st.sidebar.selectbox("Магазин:", options=acc_names, index=current_idx)
        selected_acc = next(a for a in accounts if a['name'] == selected_acc_name)
        
        if st.session_state.current_account != selected_acc:
            st.session_state.agent = WildberriesAIAgent(selected_acc['token'])
            st.session_state.current_account = selected_acc
            st.rerun()

    with st.sidebar.expander("➕ Добавить"):
        name = st.text_input("Название:")
        token = st.text_input("Токен:", type="password")
        if st.button("Сохранить"):
            if add_account(name, token): st.rerun()

    # Навигация
    if st.session_state.agent:
        st.sidebar.markdown("---")
        pages = {
            "🏠 Главная": render_home_page,
            "📊 Аналитика": render_analytics_page,
            "📦 Товары": render_products_page,
            "🤖 Автоцены": render_autoprices_page,
            "📋 Остатки": render_inventory_page,
            "💬 AI Чат": render_chat_page,
            "📢 Реклама": render_advertising_page,
            "🧾 Учет (P&L)": render_accounting_page
        }
        for p in pages.keys():
            if st.sidebar.button(p, use_container_width=True, type="primary" if st.session_state.current_page == p else "secondary"):
                st.session_state.current_page = p
                st.rerun()
        
        try: pages[st.session_state.current_page]()
        except Exception as e: st.error(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
