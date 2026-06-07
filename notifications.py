import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from db import create_connection, log_action
from groups_data import GROUPS_DATA
from constants import DEAN_LEVEL


def _send_email(smtp_cfg: dict, to_list: list, subject: str, body: str) -> tuple[bool, str]:
    """Відправляє email через SMTP. Повертає (success, message)."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_cfg['from_email']
        msg['To'] = ", ".join(to_list)

        html_body = f"""
        <html><body>
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:20px;border-radius:8px 8px 0 0">
            <h2 style="color:white;margin:0">🎓 ФМФКН — Деканат</h2>
          </div>
          <div style="padding:20px;border:1px solid #eee;border-radius:0 0 8px 8px">
            {body.replace(chr(10), '<br>')}
          </div>
          <p style="color:#999;font-size:11px;text-align:center">
            Автоматичне повідомлення від системи Project Deanery — {datetime.now().strftime('%d.%m.%Y')}
          </p>
        </div>
        </body></html>"""

        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP_SSL(smtp_cfg['server'], smtp_cfg['port']) as server:
            server.login(smtp_cfg['username'], smtp_cfg['password'])
            server.sendmail(smtp_cfg['from_email'], to_list, msg.as_string())

        return True, f"Успішно надіслано на {len(to_list)} адрес(у)"
    except smtplib.SMTPAuthenticationError:
        return False, "❌ Помилка авторизації SMTP. Перевірте логін/пароль."
    except smtplib.SMTPException as e:
        return False, f"❌ SMTP помилка: {e}"
    except Exception as e:
        return False, f"❌ Невідома помилка: {e}"


def notifications_view():
    st.title("📧 Сповіщення та Email-розсилки")

    if st.session_state.get('role') not in DEAN_LEVEL:
        st.error("Доступ заборонено. Тільки для деканату та адміністраторів.")
        return

    conn = create_connection()
    c = conn.cursor()

    tab_compose, tab_templates, tab_log = st.tabs([
        "✍️ Нова розсилка", "📋 Шаблони", "📜 Журнал відправлень"
    ])

    # ── КОНФІГУРАЦІЯ SMTP (зберігається в session_state) ─────────────────
    with st.sidebar:
        with st.expander("⚙️ SMTP налаштування", expanded=False):
            st.caption("Для Gmail: увімкніть 'App Password' у налаштуваннях Google")
            smtp_server = st.text_input("SMTP сервер", value=st.session_state.get('smtp_server', 'smtp.gmail.com'), key="smtp_srv")
            smtp_port = st.number_input("Порт", value=st.session_state.get('smtp_port', 465), key="smtp_prt")
            smtp_user = st.text_input("Email-логін", value=st.session_state.get('smtp_user', ''), key="smtp_usr")
            smtp_pass = st.text_input("Пароль / App Password", type='password',
                                      value=st.session_state.get('smtp_pass', ''), key="smtp_pw")
            smtp_from = st.text_input("From (відображуване)", value=st.session_state.get('smtp_from', ''), key="smtp_frm",
                                      placeholder="Деканат ФМФКН")
            if st.button("💾 Зберегти налаштування"):
                st.session_state.update({
                    'smtp_server': smtp_server, 'smtp_port': smtp_port,
                    'smtp_user': smtp_user, 'smtp_pass': smtp_pass,
                    'smtp_from': smtp_from or smtp_user
                })
                st.success("Збережено!")

            if st.button("🔌 Тест з'єднання"):
                cfg = {'server': smtp_server, 'port': smtp_port,
                       'username': smtp_user, 'password': smtp_pass,
                       'from_email': smtp_from or smtp_user}
                ok, msg = _send_email(cfg, [smtp_user], "Тест SMTP", "З'єднання працює!")
                if ok:
                    st.success("✅ SMTP працює!")
                else:
                    st.error(msg)

    smtp_configured = bool(st.session_state.get('smtp_user'))

    # ── НОВА РОЗСИЛКА ─────────────────────────────────────────────────────
    with tab_compose:
        if not smtp_configured:
            st.warning("⚙️ Спочатку налаштуйте SMTP у бічній панелі (ліворуч).")

        st.subheader("Отримувачі")
        recipient_mode = st.radio("Кому відправити", [
            "👥 Усій групі", "🏫 Усьому факультету", "✏️ Вручну (email-адреси)"
        ], horizontal=True)

        recipients_emails = []

        if recipient_mode == "👥 Усій групі":
            sel_group = st.selectbox("Група", list(GROUPS_DATA.keys()))
            users_df = pd.read_sql("SELECT full_name, username FROM users", conn)
            st.info(f"💡 Система надішле повідомлення студентам групи **{sel_group}** "
                    f"якщо їхні email-адреси збережені як логіни у форматі email@example.com")
            group_students = pd.read_sql(
                f"SELECT full_name FROM students WHERE group_name='{sel_group}'", conn
            )['full_name'].tolist()
            # Перевіряємо, які логіни є email'ами
            for s in group_students:
                u = users_df[users_df['full_name'] == s]
                if not u.empty:
                    uname = u.iloc[0]['username']
                    if '@' in uname:
                        recipients_emails.append(uname)
            st.caption(f"Знайдено email-адрес: {len(recipients_emails)}")

        elif recipient_mode == "🏫 Усьому факультету":
            all_users = pd.read_sql("SELECT username FROM users", conn)['username'].tolist()
            recipients_emails = [u for u in all_users if '@' in u]
            st.caption(f"Email-адрес у системі: {len(recipients_emails)}")

        else:
            manual_emails = st.text_area(
                "Email-адреси (кожна з нового рядка або через кому)",
                placeholder="student@example.com\nteacher@university.edu"
            )
            if manual_emails:
                recipients_emails = [
                    e.strip() for line in manual_emails.split('\n')
                    for e in line.split(',')
                    if '@' in e.strip()
                ]
            st.caption(f"Адрес введено: {len(recipients_emails)}")

        st.divider()
        st.subheader("Повідомлення")
        email_subject = st.text_input("Тема листа *", placeholder="Напр. Важлива інформація від деканату")
        email_body = st.text_area("Текст повідомлення *", height=200,
                                  placeholder="Шановні студенти,\n\nПовідомляємо вас про...")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            preview_btn = st.button("👁️ Попередній перегляд")
        with col_b2:
            send_btn = st.button(
                f"📤 Надіслати ({len(recipients_emails)} адрес)",
                type="primary",
                disabled=not smtp_configured or not recipients_emails or not email_subject
            )

        if preview_btn and email_subject and email_body:
            st.markdown(f"""
            <div style="border:1px solid #ccc; border-radius:8px; padding:20px;
                        background:#f9f9f9; margin-top:10px;">
                <b>Від:</b> {st.session_state.get('smtp_from', 'Деканат ФМФКН')}<br>
                <b>Кому:</b> {len(recipients_emails)} отримувачів<br>
                <b>Тема:</b> {email_subject}<br><br>
                {email_body.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)

        if send_btn:
            cfg = {
                'server': st.session_state.get('smtp_server', 'smtp.gmail.com'),
                'port': int(st.session_state.get('smtp_port', 465)),
                'username': st.session_state.get('smtp_user', ''),
                'password': st.session_state.get('smtp_pass', ''),
                'from_email': st.session_state.get('smtp_from') or st.session_state.get('smtp_user', '')
            }
            with st.spinner(f"Надсилаємо на {len(recipients_emails)} адрес(у)..."):
                ok, result_msg = _send_email(cfg, recipients_emails, email_subject, email_body)

            if ok:
                st.success(f"✅ {result_msg}")
                # Логуємо в БД
                c.execute(
                    "INSERT INTO email_log (recipients, subject, body, sent_by, sent_at, status) "
                    "VALUES (?,?,?,?,?,?)",
                    (",".join(recipients_emails), email_subject, email_body,
                     st.session_state['full_name'],
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Надіслано")
                )
                conn.commit()
                log_action(st.session_state['full_name'], "Email Sent",
                           f"Тема: {email_subject}, Отримувачів: {len(recipients_emails)}")
            else:
                st.error(result_msg)
                c.execute(
                    "INSERT INTO email_log (recipients, subject, body, sent_by, sent_at, status) "
                    "VALUES (?,?,?,?,?,?)",
                    (",".join(recipients_emails), email_subject, email_body,
                     st.session_state['full_name'],
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"Помилка: {result_msg}")
                )
                conn.commit()

    # ── ШАБЛОНИ ───────────────────────────────────────────────────────────
    with tab_templates:
        st.subheader("Готові шаблони листів")

        templates = {
            "📚 Початок сесії": {
                "subject": "Розклад сесії — ФМФКН",
                "body": "Шановні студенти!\n\nПовідомляємо, що сесія розпочинається. "
                        "Будь ласка, ознайомтесь із розкладом іспитів на сайті факультету.\n\n"
                        "Бажаємо успіхів!\nДеканат ФМФКН"
            },
            "💰 Оплата контракту": {
                "subject": "Нагадування про оплату навчання",
                "body": "Шановний студенте!\n\nНагадуємо, що термін оплати за навчання "
                        "спливає найближчим часом. Просимо своєчасно погасити заборгованість "
                        "у фінансовому відділі університету.\n\nДеканат ФМФКН"
            },
            "📋 Здача документів": {
                "subject": "Необхідно здати документи до деканату",
                "body": "Шановний студенте!\n\nПросимо Вас з'явитися до деканату "
                        "(каб. 205) для здачі необхідних документів.\n\n"
                        "Години прийому: Пн-Пт 09:00–13:00\n\nДеканат ФМФКН"
            },
            "🎓 Вітання з успіхами": {
                "subject": "Вітаємо з відмінними результатами!",
                "body": "Шановний студенте!\n\nЩиро вітаємо Вас з чудовими результатами "
                        "навчання! Ваша старанність та відданість навчанню заслуговують "
                        "найвищої похвали. Бажаємо подальших успіхів!\n\nДеканат ФМФКН"
            }
        }

        for tmpl_name, tmpl_data in templates.items():
            with st.expander(tmpl_name):
                st.write(f"**Тема:** {tmpl_data['subject']}")
                st.write(f"**Текст:**\n{tmpl_data['body']}")
                if st.button(f"Використати шаблон", key=f"tmpl_{tmpl_name}"):
                    st.session_state['email_template'] = tmpl_data
                    st.success("Шаблон скопійовано! Перейдіть на вкладку **Нова розсилка**.")

    # ── ЖУРНАЛ ────────────────────────────────────────────────────────────
    with tab_log:
        st.subheader("📜 Журнал відправлень")
        log_df = pd.read_sql(
            "SELECT id, subject, sent_by, sent_at, status, "
            "length(recipients)-length(replace(recipients,',',''))+1 as count "
            "FROM email_log ORDER BY id DESC",
            conn
        )
        if not log_df.empty:
            log_df.columns = ['ID', 'Тема', 'Відправник', 'Дата', 'Статус', 'Кількість']
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("Жодного листа ще не надіслано.")
