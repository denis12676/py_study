import logging
import streamlit as st
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_agent import WildberriesAIAgent
from styles import get_dark_theme_css
from logging_config import setup_logging
from database import run_query, init_db_tables
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
    if st.session_state.user is None:
        session_id = st.query_params.get("session")
        if session_id:
            user = get_user_by_session(session_id)
            if user:
                st.session_state.user = user
                return True
    return False

def render_auth():
    st.markdown("<h1 style='text-align: center;'>🛍️ MultiMarket AI</h1>", unsafe_allow_html=True)
    choice = st.radio("Выберите действие:", ["Вход", "Регистрация"], horizontal=True)
    with st.form("auth_form"):
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        if st.form_submit_button("Выполнить"):
            if choice == "Регистрация":
                if create_user(username, password): st.success("Успешно! Войдите.")
                else: st.error("Ошибка регистрации.")
            else:
                user = login_user(username, password)
                if user:
                    sid = start_session(user['id'])
                    st.query_params["session"] = sid
                    st.session_state.user = user
                    st.rerun()
                else: st.error("Неверный логин или пароль")
    st.stop()

def logout():
    sid = st.query_params.get("session")
    if sid: close_session(sid)
    st.query_params.clear()
    st.session_state.user = None
    st.session_state.agent = None
    st.rerun()

# --- Database Helpers ---
def get_accounts():
    user_id = st.session_state.user['id']
    return run_query("SELECT * FROM accounts WHERE user_id = :uid ORDER BY name", {"uid": user_id})

def add_account(name, token):
    user_id = st.session_state.user['id']
    try:
        run_query("INSERT INTO accounts (name, token, user_id) VALUES (:n, :t, :uid)", 
                 {"n": name, "t": token, "uid": user_id}, is_select=False)
        return True
    except: return False

# --- Main App ---
def main():
    st.set_page_config(page_title="MultiMarket AI", page_icon="🛍️", layout="wide")
    st.markdown(get_dark_theme_css(), unsafe_allow_html=True)
    check_auth_persistence()
    if not st.session_state.user: render_auth()

    st.sidebar.markdown(f"👤 **Пользователь:** {st.session_state.user['username']}")
    if st.sidebar.button("🚪 Выйти"): logout()

    st.sidebar.markdown("---")
    accounts = get_accounts()
    if not accounts: st.sidebar.warning("Добавьте магазин")
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
