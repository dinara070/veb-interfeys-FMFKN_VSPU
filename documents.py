import streamlit as st
import pandas as pd
from datetime import datetime

from database import create_connection
from config import DEAN_LEVEL


def documents_view():
    st.title("📂 Документообіг та Заяви")
    conn = create_connection()

    tabs_list = ["📂 Реєстр / Мої заяви", "➕ Створити заяву"]
    show_admin = st.session_state['role'] in DEAN_LEVEL
    if show_admin:
        tabs_list.append("⚙️ Обробка запитів")

    tabs = st.tabs(tabs_list)

    with tabs[0]:
        st.subheader("Історія документів")
        if st.session_state['role'] in ['student', 'starosta']:
            query = (
                f"SELECT id, title as 'Тип документу', status as 'Статус', date as 'Дата подачі' "
                f"FROM documents WHERE student_name='{st.session_state['full_name']}' ORDER BY id DESC"
            )
        else:
            c1, c2 = st.columns([1, 3])
            filter_status = c1.selectbox("Фільтр за статусом", ["Всі", "Очікує", "Готово", "Відхилено"])
            base_q = ("SELECT id, student_name as 'Студент', title as 'Тип документу', "
                      "status as 'Статус', date as 'Дата' FROM documents")
            query = (
                f"{base_q} WHERE status LIKE '{filter_status}%' ORDER BY id DESC"
                if filter_status != "Всі"
                else f"{base_q} ORDER BY id DESC"
            )

        try:
            df_docs = pd.read_sql(query, conn)
            if not df_docs.empty:
                st.dataframe(df_docs, use_container_width=True)
            else:
                st.info("Список документів порожній")
        except Exception as e:
            st.error(f"Помилка завантаження даних: {e}")

    with tabs[1]:
        st.subheader("Подання нового запиту")
        with st.form("doc_create"):
            d_type = st.selectbox("Тип документу", [
                "Довідка про навчання (для ТЦК/Військкомату)",
                "Довідка про навчання (за місцем вимоги)",
                "Довідка про доходи",
                "Виписка з оцінками (Transcript)",
                "Заява на матеріальну допомогу",
                "Заява на поселення в гуртожиток",
                "Заява на індивідуальний графік"
            ])
            d_comment = st.text_input("Додаткові примітки (напр. 'В ТЦК м. Вінниця' або 'Терміново')")

            if st.form_submit_button("Надіслати запит"):
                full_title = f"{d_type}" + (f" ({d_comment})" if d_comment else "")
                conn.execute(
                    "INSERT INTO documents (title, student_name, status, date) VALUES (?,?,?,?)",
                    (full_title, st.session_state['full_name'], "Очікує", str(datetime.now().date()))
                )
                conn.commit()
                st.success("Запит успішно надіслано!")
                st.rerun()

    if show_admin:
        with tabs[2]:
            st.subheader("⚙️ Обробка запитів студентів")
            pending_docs = pd.read_sql(
                "SELECT id, student_name, title, date FROM documents WHERE status='Очікує'", conn
            )

            if not pending_docs.empty:
                st.warning(f"Необроблених запитів: {len(pending_docs)}")
                req_id = st.selectbox(
                    "Оберіть запит", pending_docs['id'].tolist(),
                    format_func=lambda x: f"ID {x}"
                )
                sel_row = pending_docs[pending_docs['id'] == req_id].iloc[0]

                with st.container(border=True):
                    st.markdown(f"**Студент:** {sel_row['student_name']} | **Запит:** {sel_row['title']}")
                    ac1, ac2 = st.columns(2)
                    new_status = ac1.selectbox("Рішення", ["Готово", "Відхилено", "В роботі"])
                    admin_comment = ac2.text_input("Коментар", placeholder="каб. 205")

                    if st.button("✅ Застосувати рішення"):
                        final_status = new_status + (f" ({admin_comment})" if admin_comment else "")
                        conn.execute("UPDATE documents SET status=? WHERE id=?", (final_status, req_id))
                        conn.commit()
                        st.success("Статус оновлено")
                        st.rerun()
            else:
                st.success("🎉 Всі запити опрацьовано!")
