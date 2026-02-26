import streamlit as st
from sqlalchemy import create_engine, text
from pathlib import Path
import os

# Путь к локальной БД для разработки
LOCAL_DB = f"sqlite:///{Path(__file__).parent}/wb_cache.db"

def get_engine():
    """
    Возвращает движок БД. 
    Если в Secrets прописан DATABASE_URL — использует его (Postgres),
    иначе использует локальный SQLite.
    """
    db_url = st.secrets.get("DATABASE_URL")
    if not db_url:
        # Fallback на переменную окружения для Docker/Local
        db_url = os.getenv("DATABASE_URL", LOCAL_DB)
    
    # SQLAlchemy требует чтобы URL начинался с postgresql:// вместо postgres:// (фикс для Render/Heroku/Supabase)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(db_url)

def run_query(query, params=None, is_select=True):
    """Универсальная функция выполнения запросов"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        if not is_select:
            conn.commit()
            return None
        
        # Возвращаем список словарей
        if result.returns_rows:
            return [dict(row._mapping) for row in result]
        return []

def init_db_tables():
    """Создание таблиц если их нет"""
    # SQL для создания таблиц (совместимый и с SQLite и с Postgres)
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, 
            username TEXT UNIQUE, 
            password_hash TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            expires_at TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            token TEXT,
            marketplace TEXT DEFAULT 'wb'
        )""",
        """CREATE TABLE IF NOT EXISTS product_costs (
            nm_id BIGINT PRIMARY KEY,
            user_id INTEGER,
            vendor_code TEXT,
            purchase_price REAL,
            tax_percent REAL DEFAULT 6.0
        )""",
        """CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            category TEXT,
            amount REAL,
            date TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS financial_reports (
            user_id INTEGER,
            report_date TEXT,
            nm_id BIGINT,
            vendor_code TEXT,
            subject_name TEXT,
            brand_name TEXT,
            supplier_oper_name TEXT,
            retail_amount REAL,
            for_pay REAL,
            commission REAL,
            delivery REAL,
            storage REAL,
            penalty REAL,
            quantity INTEGER,
            is_return BOOLEAN,
            PRIMARY KEY (user_id, report_date, nm_id, supplier_oper_name, retail_amount)
        )"""
    ]
    
    engine = get_engine()
    with engine.begin() as conn:
        for q in queries:
            # Для SQLite заменяем SERIAL на INTEGER PRIMARY KEY AUTOINCREMENT
            if engine.name == 'sqlite':
                q = q.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                q = q.replace("BIGINT PRIMARY KEY", "INTEGER PRIMARY KEY")
                q = q.replace("TIMESTAMP", "DATETIME")
            conn.execute(text(q))
