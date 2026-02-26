import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "wb_cache.db"

def init_db():
    """Инициализация всех таблиц базы данных если они не существуют"""
    with sqlite3.connect(DB_PATH) as conn:
        # Таблица пользователей
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password_hash TEXT
            )
        """)
        # Таблица магазинов (аккаунтов)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                token TEXT,
                marketplace TEXT DEFAULT 'wb'
            )
        """)
        # Таблица себестоимости
        conn.execute("""
            CREATE TABLE IF NOT EXISTS product_costs (
                nm_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                vendor_code TEXT,
                purchase_price REAL,
                tax_percent REAL DEFAULT 6.0
            )
        """)
        # Таблица расходов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                date TEXT
            )
        """)
        # Таблица финансовых отчетов (кэш)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_reports (
                user_id INTEGER,
                report_date TEXT,
                nm_id INTEGER,
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
            )
        """)
        conn.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password):
    init_db() # Убеждаемся что таблицы созданы
    try:
        pw_hash = hash_password(password)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    init_db() # Убеждаемся что таблицы созданы
    pw_hash = hash_password(password)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, pw_hash)).fetchone()
        return dict(user) if user else None
