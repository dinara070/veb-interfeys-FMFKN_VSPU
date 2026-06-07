import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from streamlit_cookies_controller import CookieController

from db import make_hashes, log_action, create_connection
from constants import ROLES_LIST

controller = CookieController()

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def _get_attempts(username: str):
    conn = create_connection()
    row = conn.execute(
        "SELECT attempts, locked_until FROM login_attempts WHERE username=?", (username,)
    ).fetchone()
    conn.close()
    return row  # (attempts, locked_until) або None


def _reset_attempts(username: str):
    conn = create_connection()
    conn.execute("DELETE FROM login_attempts WHERE username=?", (username,))
    conn.commit()
    conn.close()


def _increment_attempts(username: str):
    conn = create_connection()
    row = conn.execute(
        "SELECT attempts FROM login_attempts WHERE username=?", (username,)
    ).fetchone()
    attempts = (row[0] + 1) if row else 1
    locked_until = ""
    if attempts >= MAX_ATTEMPTS:
        locked_until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT OR REPLACE INTO login_attempts (username, attempts, locked_until) VALUES (?,?,?)",
        (username, attempts, locked_until)
    )
    conn.commit()
    conn.close()
    return attempts, locked_until


def _is_locked(username: str):
    row = _get_attempts(username)
    if not row:
        return False, 0
    attempts, locked_until = row
    if locked_until:
        lock_dt = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < lock_dt:
            remaining = int((lock_dt - datetime.now()).total_seconds() / 60) + 1
            return True, remaining
        else:
            _reset_attempts(username)
    return False, 0


def perform_login(user):
    st.session_state['logged_in'] = True
    st.session_state['username'] = user[0]
    st.session_state['role'] = user[2]
    st.session_state['full_name'] = user[3]
    st.session_state['group'] = user[4]
    st.session_state['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    controller.set('remember_user', user[0])
    _reset_attempts(user[0])
    log_action(user[3], "Login", "Вхід у систему")
    st.success(f"Вітаємо, {user[3]}!")
    st.rerun()


def login_register_page():
    # Мобільний CSS + покращений стиль сторінки входу
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        [data-testid="stSidebar"] { display: none; }
        .block-container { padding: 1rem !important; }
    }
    .login-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2px; border-radius: 16px; margin-bottom: 1rem;
    }
    .login-inner {
        background: var(--background-color, #fff);
        border-radius: 14px; padding: 2rem;
    }
    .brand-title {
        font-size: 1.8rem; font-weight: 800; text-align: center;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="brand-title">🎓 Project Deanery</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#888;margin-top:-0.5rem;">ФМФКН — Система управління деканатом</p>', unsafe_allow_html=True)
        st.markdown("")

        mode = st.tabs(["🔐 Увійти", "📝 Реєстрація"])
        conn = create_connection()
        c = conn.cursor()

        # ── ВХІД ──────────────────────────────────────────────────────────
        with mode[0]:
            saved_username = controller.get('remember_user')
            username = st.text_input(
                "Ім'я користувача:",
                value=saved_username if saved_username else "",
                key="login_user",
                placeholder="Введіть логін"
            )
            password = st.text_input("Пароль:", type='password', key="login_pass",
                                     placeholder="Введіть пароль")

            # Капча
            st.divider()
            captcha_val = "56388"
            col_c1, col_c2 = st.columns([1, 2])
            with col_c1:
                st.markdown("**Код підтвердження:**")
                st.code(captcha_val, language=None)
            with col_c2:
                user_captcha = st.text_input("Введіть код:", key="login_captcha", label_visibility="collapsed",
                                             placeholder="Введіть код вище")

            if st.button("🚀 Увійти в систему", use_container_width=True, type="primary"):
                if not username or not password:
                    st.warning("⚠️ Заповніть усі поля.")
                elif user_captcha != captcha_val:
                    st.error("❌ Невірний код підтвердження.")
                else:
                    # Перевірка блокування
                    locked, minutes_left = _is_locked(username)
                    if locked:
                        st.error(f"🔒 Акаунт тимчасово заблоковано. Спробуйте через {minutes_left} хв.")
                    else:
                        hashed_input = make_hashes(password)
                        c.execute('SELECT * FROM users WHERE username=? AND password=?',
                                  (username, hashed_input))
                        user = c.fetchone()
                        if user:
                            perform_login(user)
                        else:
                            attempts, locked_until = _increment_attempts(username)
                            left = MAX_ATTEMPTS - attempts
                            if locked_until:
                                st.error(f"🔒 Забагато спроб! Акаунт заблоковано на {LOCK_MINUTES} хв.")
                            else:
                                st.error(f"❌ Невірний логін або пароль. Залишилось спроб: {left}")

        # ── РЕЄСТРАЦІЯ ────────────────────────────────────────────────────
        with mode[1]:
            st.info("Реєстрація одноразова — ваш акаунт збережеться назавжди.")
            new_user = st.text_input("Логін:", key="reg_user_new", placeholder="Унікальний логін")
            new_pass = st.text_input("Пароль:", type='password', key="reg_pass_new",
                                     placeholder="Мінімум 6 символів")
            new_pass2 = st.text_input("Повторіть пароль:", type='password', key="reg_pass2",
                                      placeholder="Підтвердження пароля")
            full_name = st.text_input("Повне ПІБ:", key="reg_full_name",
                                      placeholder="Прізвище Ім'я По батькові")
            role_choice = st.selectbox("Посада:", ROLES_LIST, key="reg_role_select")

            # Індикатор надійності пароля
            if new_pass:
                strength = sum([
                    len(new_pass) >= 8,
                    any(c.isupper() for c in new_pass),
                    any(c.isdigit() for c in new_pass),
                    any(c in "!@#$%^&*" for c in new_pass)
                ])
                colors = ["#ff4444", "#ff8800", "#ffcc00", "#44bb44"]
                labels = ["Слабкий", "Задовільний", "Добрий", "Надійний"]
                st.markdown(
                    f'<div style="height:6px;border-radius:3px;background:{colors[strength-1]};'
                    f'width:{strength*25}%;margin-bottom:4px"></div>'
                    f'<small style="color:{colors[strength-1]}">Пароль: {labels[strength-1]}</small>',
                    unsafe_allow_html=True
                )

            if st.button("✅ Створити акаунт", use_container_width=True, type="primary"):
                if not all([new_user, new_pass, full_name]):
                    st.warning("⚠️ Заповніть усі поля.")
                elif new_pass != new_pass2:
                    st.error("❌ Паролі не співпадають.")
                elif len(new_pass) < 6:
                    st.error("❌ Пароль занадто короткий (мінімум 6 символів).")
                else:
                    try:
                        hashed_pw = make_hashes(new_pass)
                        c.execute(
                            'INSERT INTO users (username, password, role, full_name, group_link) VALUES (?,?,?,?,?)',
                            (new_user, hashed_pw, role_choice, full_name, "Staff")
                        )
                        conn.commit()
                        controller.set('remember_user', new_user)
                        st.success("🎉 Акаунт створено! Перейдіть на вкладку **Увійти**.")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Цей логін вже зайнятий.")
