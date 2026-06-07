import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_cookies_controller import CookieController

from db import make_hashes, log_action, create_connection
from constants import ROLES_LIST

controller = CookieController()


def perform_login(user):
    st.session_state['logged_in'] = True
    st.session_state['username'] = user[0]
    st.session_state['role'] = user[2]
    st.session_state['full_name'] = user[3]
    st.session_state['group'] = user[4]
    controller.set('remember_user', user[0])
    log_action(user[3], "Login", "Вхід у систему")
    st.success(f"Вітаємо, {user[3]}!")
    st.rerun()


def login_register_page():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h2 style='text-align: center;'>🎓 Project Deanery .net</h2>", unsafe_allow_html=True)

        mode = st.tabs(["🔐 Увійти", "📝 Реєстрація"])
        conn = create_connection()
        c = conn.cursor()

        # --- ВКЛАДКА ВХОДУ ---
        with mode[0]:
            saved_username = controller.get('remember_user')
            username = st.text_input("Ім'я користувача (Username):",
                                     value=saved_username if saved_username else "",
                                     key="login_user")
            password = st.text_input("Пароль:", type='password', key="login_pass")

            st.divider()
            captcha_val = "56388"
            st.markdown("**Код підтвердження:**")
            st.code(captcha_val, language=None)
            user_captcha = st.text_input("Введіть код, який ви бачите вище:", key="login_captcha")

            if st.button("Увійти в систему", use_container_width=True):
                if user_captcha != captcha_val:
                    st.error("❌ Невірний код підтвердження. Спробуйте ще раз.")
                elif username and password:
                    hashed_input = make_hashes(password)
                    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, hashed_input))
                    user = c.fetchone()
                    if user:
                        perform_login(user)
                    else:
                        st.error("❌ Користувача не знайдено або пароль невірний.")
                else:
                    st.warning("⚠️ Будь ласка, заповніть усі поля для входу.")

        # --- ВКЛАДКА РЕЄСТРАЦІЇ ---
        with mode[1]:
            st.markdown("### Первинна реєстрація")
            st.info("Ви реєструєтесь один раз. Після цього ваш акаунт буде зберігатися в базі постійно.")

            new_user = st.text_input("Придумайте унікальний логін:", key="reg_user_new")
            new_pass = st.text_input("Придумайте надійний пароль:", type='password', key="reg_pass_new")
            full_name = st.text_input("Ваше повне ПІБ (напр. Іванов Іван Іванович):", key="reg_full_name")
            role_choice = st.selectbox("Оберіть вашу посаду:", ROLES_LIST, key="reg_role_select")

            if st.button("Створити обліковий запис", use_container_width=True):
                if new_user and new_pass and full_name:
                    try:
                        hashed_pw = make_hashes(new_pass)
                        c.execute(
                            'INSERT INTO users (username, password, role, full_name, group_link) VALUES (?,?,?,?,?)',
                            (new_user, hashed_pw, role_choice, full_name, "Staff")
                        )
                        conn.commit()
                        controller.set('remember_user', new_user)
                        st.success("🎉 Реєстрація успішна! Ваш акаунт створено та внесено в базу.")
                        st.info("Тепер просто перейдіть на вкладку **'🔐 Увійти'** — ваш логін вже підставлено.")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Цей логін вже зайнятий. Будь ласка, оберіть інший.")
                else:
                    st.warning("⚠️ Для реєстрації необхідно заповнити всі доступні поля.")
