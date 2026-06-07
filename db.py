import sqlite3
import hashlib
import pandas as pd
from datetime import datetime
from groups_data import GROUPS_DATA


def create_connection():
    return sqlite3.connect('university_v22.db', check_same_thread=False)


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


def log_action(user, action, details):
    conn = create_connection()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO system_logs (user, action, details, timestamp) VALUES (?,?,?,?)",
        (user, action, details, ts)
    )
    conn.commit()


def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')


def init_db():
    conn = create_connection()
    c = conn.cursor()

    # 1. Основні таблиці
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, full_name TEXT, group_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, group_name TEXT)''')

    # 2. Навчальний процес
    c.execute('''CREATE TABLE IF NOT EXISTS schedule
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, day TEXT, time TEXT, subject TEXT, teacher TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS grades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, type_of_work TEXT, grade INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, date_column TEXT, status TEXT)''')

    # 3. Деканат та Соціальні модулі
    c.execute('''CREATE TABLE IF NOT EXISTS dormitory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, room_number TEXT, payment_status TEXT, comments TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scholarship
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, type TEXT, amount INTEGER, status TEXT, date_assigned TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS student_contracts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, contract_number TEXT, date_signed TEXT, end_date TEXT, total_amount REAL, paid_amount REAL, payment_status TEXT, notes TEXT)''')

    # 4. Документообіг та Сесія
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, student_name TEXT, status TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sheets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, sheet_number TEXT, group_name TEXT, subject TEXT, control_type TEXT, exam_date TEXT, examiner TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS individual_statements
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, subject TEXT, statement_type TEXT, reason TEXT, date_issued TEXT, status TEXT, created_by TEXT)''')

    # 5. Спеціалізовані дані (Анкети)
    c.execute('''CREATE TABLE IF NOT EXISTS student_education_info
                 (student_name TEXT PRIMARY KEY, status TEXT, study_form TEXT, course INTEGER, is_contract TEXT, faculty TEXT, specialty TEXT, edu_program TEXT, referral_type TEXT, enterprise TEXT, enroll_protocol_num TEXT, enroll_order_num TEXT, enroll_condition TEXT, enroll_protocol_date TEXT, enroll_order_date TEXT, enroll_date TEXT, grad_order_num TEXT, grad_order_date TEXT, grad_date TEXT, student_id_card TEXT, gradebook_id TEXT, library_card TEXT, curator TEXT, last_modified TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS student_prev_education
                 (student_name TEXT PRIMARY KEY, institution_name TEXT, institution_type TEXT, diploma_type TEXT, diploma_series TEXT, diploma_number TEXT, diploma_grades_summary TEXT, foreign_languages TEXT, last_modified TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS academic_certificates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, cert_number TEXT, issue_date TEXT, source_institution TEXT, notes TEXT, added_by TEXT, added_date TEXT)''')

    # 6. Системні таблиці
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, author TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, details TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS file_storage
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, file_content BLOB, upload_date TEXT, uploader TEXT, subject TEXT, description TEXT)''')

    conn.commit()

    # --- АВТОМАТИЧНЕ ЗАПОВНЕННЯ (якщо база порожня) ---
    c.execute('SELECT count(*) FROM students')
    if c.fetchone()[0] == 0:
        c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)',
                  ('admin', make_hashes('admin'), 'admin', 'Головний Адміністратор', ''))

        for group, names in GROUPS_DATA.items():
            for name in names:
                clean_name = name.lstrip("0123456789. ")
                c.execute('INSERT INTO students (full_name, group_name) VALUES (?,?)', (clean_name, group))
        conn.commit()

    return conn
