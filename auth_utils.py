import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "wb_cache.db"

def hash_password(password: str) -> str:
    """Хеширование пароля для безопасности"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password):
    """Регистрация нового пользователя"""
    try:
        pw_hash = hash_password(password)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            return True
    except sqlite3.IntegrityError:
        return False # Пользователь уже существует

def login_user(username, password):
    """Проверка логина и пароля"""
    pw_hash = hash_password(password)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, pw_hash)).fetchone()
        return dict(user) if user else None
