# ui/auth.py
def login_register_page():
    """Оновлена сторінка входу та реєстрації з тривалим збереженням даних"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h2 style='text-align: center;'>🎓 Project Deanery .net</h2>", unsafe_allow_html=True)

        # Вибір режиму: Вхід або Реєстрація через вкладки
        mode = st.tabs(["🔐 Увійти", "📝 Реєстрація"])

        conn = create_connection()
        c = conn.cursor()

        # --- ВКЛАДКА ВХОДУ ---
        with mode[0]:
            # Читаємо збережений логін з кукі браузера (ключ remember_user)
            saved_username = controller.get('remember_user')

            username = st.text_input("Ім'я користувача (Username):", value=saved_username if saved_username else "", key="login_user")
            password = st.text_input("Пароль:", type='password', key="login_pass")

            # Блок Капчі (цифровий код підтвердження)
            st.divider()
            captcha_val = "56388"
            st.markdown(f"**Код підтвердження:**")
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
                        st.error("❌ Користувача не знайдено або пароль невірний. Перевірте дані.")
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
                        # Записуємо в базу даних. Ці дані залишаться в файлі .db
                        c.execute('INSERT INTO users (username, password, role, full_name, group_link) VALUES (?,?,?,?,?)',
                                  (new_user, hashed_pw, role_choice, full_name, "Staff"))
                        conn.commit()

                        # Зберігаємо логін в кукі, щоб поле 'Username' у вкладці входу заповнилося автоматично
                        controller.set('remember_user', new_user)

                        st.success("🎉 Реєстрація успішна! Ваш акаунт створено та внесено в базу.")
                        st.info("Тепер просто перейдіть на вкладку **'🔐 Увійти'** — ваш логін вже підставлено.")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Цей логін вже зайнятий. Будь ласка, оберіть інший.")
                else:
                    st.warning("⚠️ Для реєстрації необхідно заповнити всі доступні поля.")
