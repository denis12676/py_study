import hashlib
import sqlite3
import uuid
import secrets
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "wb_cache.db"

def init_db():
    """Инициализация всех таблиц базы данных"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password_hash TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                expires_at DATETIME
            )
        """)
        # Остальные таблицы (accounts, product_costs, и т.д. - оставляем как было)
        conn.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, token TEXT, marketplace TEXT DEFAULT 'wb')")
        conn.execute("CREATE TABLE IF NOT EXISTS product_costs (nm_id INTEGER PRIMARY KEY, user_id INTEGER, vendor_code TEXT, purchase_price REAL, tax_percent REAL DEFAULT 6.0)")
        conn.execute("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, category TEXT, amount REAL, date TEXT)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_reports (
                user_id INTEGER, report_date TEXT, nm_id INTEGER, vendor_code TEXT,
                subject_name TEXT, brand_name TEXT, supplier_oper_name TEXT,
                retail_amount REAL, for_pay REAL, commission REAL,
                delivery REAL, storage REAL, penalty REAL, quantity INTEGER,
                is_return BOOLEAN,
                PRIMARY KEY (user_id, report_date, nm_id, supplier_oper_name, retail_amount)
            )
        """)
        conn.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password):
    init_db()
    try:
        pw_hash = hash_password(password)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    init_db()
    pw_hash = hash_password(password)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, pw_hash)).fetchone()
        return dict(user) if user else None

# --- Session Management ---

def start_session(user_id: int) -> str:
    """Создает новую сессию в БД и возвращает её ID"""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=1) # Сессия на 24 часа
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)", 
                    (session_id, user_id, expires_at.isoformat()))
        conn.commit()
    return session_id

def get_user_by_session(session_id: str):
    """Проверяет валидность сессии и возвращает данные пользователя"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        now = datetime.now().isoformat()
        row = conn.execute("""
            SELECT u.* FROM users u 
            JOIN sessions s ON u.id = s.user_id 
            WHERE s.session_id = ? AND s.expires_at > ?
        """, (session_id, now)).fetchone()
        return dict(row) if row else None

def close_session(session_id: str):
    """Удаляет сессию при выходе"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
