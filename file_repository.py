import streamlit as st
import pandas as pd
from datetime import datetime

# ... (ваші імпорти)

def file_repository_view():
    st.title("🗄️ Файловий Репозиторій")
    conn = create_connection()
    c = conn.cursor()

    # --- ДОДАНО: Розширені фільтри ---
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        filter_subj = st.selectbox("📂 Фільтр по предмету", ["Всі"] + SUBJECTS_LIST)
    with col_f2:
        search_query = st.text_input("🔍 Пошук за назвою або описом")

    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📤 Завантажити новий файл"):
            with st.form("upload_form", clear_on_submit=True):
                uploaded_file = st.file_uploader("Виберіть файл", accept_multiple_files=False)
                f_subject = st.selectbox("Предмет", SUBJECTS_LIST)
                f_desc = st.text_input("Опис")
                if st.form_submit_button("Зберегти"):
                    if uploaded_file and f_desc:
                        # Зберігаємо файл як blob
                        c.execute(
                            "INSERT INTO file_storage (filename, file_content, upload_date, uploader, subject, description, file_size) VALUES (?,?,?,?,?,?,?)",
                            (uploaded_file.name, uploaded_file.read(), datetime.now().strftime("%Y-%m-%d %H:%M"), 
                             st.session_state['full_name'], f_subject, f_desc, uploaded_file.size)
                        )
                        conn.commit()
                        st.success("Файл успішно завантажено!")
                        st.rerun()
                    else:
                        st.warning("Будь ласка, заповніть всі поля.")

    # --- ДОДАНО: Логіка пошуку ---
    query = "SELECT id, filename, subject, description, upload_date, uploader, file_size FROM file_storage WHERE 1=1"
    params = []
    
    if filter_subj != "Всі":
        query += " AND subject=?"
        params.append(filter_subj)
    
    if search_query:
        query += " AND (filename LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    df_files = pd.read_sql_query(query, conn, params=params)

    if not df_files.empty:
        for s in df_files['subject'].unique():
            st.subheader(f"📘 {s}")
            for _, row in df_files[df_files['subject'] == s].iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
                    c1.write(f"📄 **{row['filename']}**")
                    c2.write(f"📝 {row['description']}")
                    # Відображаємо розмір у КБ
                    size_kb = round(row['file_size'] / 1024, 1)
                    c3.caption(f"👤 {row['uploader']} | 💾 {size_kb} KB")
                    
                    # Кнопка завантаження
                    data = c.execute("SELECT file_content FROM file_storage WHERE id=?", (row['id'],)).fetchone()[0]
                    c3.download_button("⬇️ Завантажити", data, row['filename'], key=f"d{row['id']}")
                    
                    if st.session_state['role'] == 'admin':
                        if c4.button("🗑️", key=f"del_{row['id']}", help="Видалити файл"):
                            c.execute("DELETE FROM file_storage WHERE id=?", (row['id'],))
                            conn.commit()
                            st.rerun()
    else:
        st.info("Файлів не знайдено.")
