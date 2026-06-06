# database/db_core.py
import sqlite3
import hashlib
from datetime import datetime

def create_connection():
    return sqlite3.connect('university_v22.db', check_same_thread=False)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def log_action(user, action, details):
    conn = create_connection()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO system_logs (user, action, details, timestamp) VALUES (?,?,?,?)", 
                 (user, action, details, ts))
    conn.commit()
    conn.close()

def init_db():
    conn = create_connection()
    c = conn.cursor()
    # Створення всіх таблиць (усі c.execute з вашого коду тут)
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, full_name TEXT, group_link TEXT)''')
    # ... (інші таблиці)
    conn.commit()
    conn.close()
