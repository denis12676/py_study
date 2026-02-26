import hashlib
import secrets
from datetime import datetime, timedelta
from database import run_query, init_db_tables

def init_db():
    init_db_tables()

def hash_password(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user(username, password):
    pw_hash = hash_password(password)
    try:
        run_query("INSERT INTO users (username, password_hash) VALUES (:u, :p)", 
                 {"u": username, "p": pw_hash}, is_select=False)
        return True
    except:
        return False

def login_user(username, password):
    pw_hash = hash_password(password)
    rows = run_query("SELECT * FROM users WHERE username = :u AND password_hash = :p", 
                    {"u": username, "p": pw_hash})
    return rows[0] if rows else None

def start_session(user_id: int) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=1)
    run_query("INSERT INTO sessions (session_id, user_id, expires_at) VALUES (:sid, :uid, :exp)", 
             {"sid": session_id, "uid": user_id, "exp": expires_at}, is_select=False)
    return session_id

def get_user_by_session(session_id: str):
    now = datetime.now()
    rows = run_query("""
        SELECT u.* FROM users u 
        JOIN sessions s ON u.id = s.user_id 
        WHERE s.session_id = :sid AND s.expires_at > :now
    """, {"sid": session_id, "now": now})
    return rows[0] if rows else None

def close_session(session_id: str):
    run_query("DELETE FROM sessions WHERE session_id = :sid", {"sid": session_id}, is_select=False)
