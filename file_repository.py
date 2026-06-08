import streamlit as st
import pandas as pd
from datetime import datetime

from db import create_connection
from constants import SUBJECTS_LIST, TEACHER_LEVEL


def file_repository_view():
    st.title("🗄️ Файловий Репозиторій")
    conn = create_connection()
    c = conn.cursor()

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        filter_subj = st.selectbox("📂 Фільтр по предмету", ["Всі"] + SUBJECTS_LIST)

    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📤 Завантажити"):
            with st.form("upload_form"):
                uploaded_file = st.file_uploader("Файл", accept_multiple_files=False)
                f_subject = st.selectbox("Предмет", SUBJECTS_LIST)
                f_desc = st.text_input("Опис")
                if st.form_submit_button("Зберегти"):
                    if uploaded_file and f_desc:
                        c.execute(
                            "INSERT INTO file_storage "
                            "(filename, file_content, upload_date, uploader, subject, description) "
                            "VALUES (?,?,?,?,?,?)",
                            (
                                uploaded_file.name,
                                uploaded_file.read(),
                                datetime.now().strftime("%Y-%m-%d %H:%M"),
                                st.session_state['full_name'],
                                f_subject,
                                f_desc
                            )
                        )
                        conn.commit()
                        st.success("Збережено!")
                        st.rerun()

    query = "SELECT id, filename, subject, description, upload_date, uploader FROM file_storage"
    if filter_subj != "Всі":
        query += f" WHERE subject='{filter_subj}'"
    df_files = pd.read_sql_query(query, conn)

    if not df_files.empty:
        for s in df_files['subject'].unique():
            st.subheader(f"📘 {s}")
            for i, row in df_files[df_files['subject'] == s].iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 4, 2, 1])
                    c1.write(f"📄 **{row['filename']}**")
                    c2.write(f"📝 {row['description']}")
                    c3.caption(f"{row['uploader']}")
                    data = c.execute(
                        "SELECT file_content FROM file_storage WHERE id=?", (row['id'],)
                    ).fetchone()[0]
                    c3.download_button("⬇️", data, row['filename'], key=f"d{row['id']}")
                    if st.session_state['role'] == 'admin':
                        if c4.button("🗑️", key=f"del_{row['id']}"):
                            c.execute("DELETE FROM file_storage WHERE id=?", (row['id'],))
                            conn.commit()
                            st.rerun()
    else:
        st.info("Наразі дані не завантажені.")
