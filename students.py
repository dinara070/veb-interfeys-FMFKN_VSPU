import streamlit as st
import pandas as pd

from db import create_connection, log_action, convert_df_to_csv
from groups_data import GROUPS_DATA
from constants import DEAN_LEVEL


def students_groups_view():
    st.title("👥 Студенти та Групи")
    conn = create_connection()

    all_groups = ["Всі"] + list(GROUPS_DATA.keys())
    selected_group = st.selectbox("Фільтр по групі:", all_groups)

    query = "SELECT id, full_name as 'ПІБ', group_name as 'Група' FROM students"
    if selected_group != "Всі":
        query += f" WHERE group_name='{selected_group}'"
    df = pd.read_sql_query(query, conn)

    csv = convert_df_to_csv(df)
    st.download_button("⬇️ Експортувати (CSV)", csv, "students.csv", "text/csv")
    st.dataframe(df, use_container_width=True)

    if st.session_state['role'] in DEAN_LEVEL:
        st.divider()
        st.subheader("🛠️ Управління")
        t1, t2, t3 = st.tabs(["➕ Додати", "📥 Імпорт", "🗑️ Видалити"])

        with t1:
            with st.form("add_s"):
                nm = st.text_input("ПІБ")
                gr = st.selectbox("Група", list(GROUPS_DATA.keys()))
                if st.form_submit_button("Додати"):
                    c = conn.cursor()
                    c.execute('INSERT INTO students (full_name, group_name) VALUES (?,?)', (nm, gr))
                    conn.commit()
                    log_action(st.session_state['full_name'], "Add Student", f"Додано: {nm} в {gr}")
                    st.success("Додано!")
                    st.rerun()

        with t2:
            if st.session_state['role'] in ['admin', 'dean']:
                f = st.file_uploader("CSV (full_name, group_name)", type="csv")
                if f:
                    try:
                        df_new = pd.read_csv(f)
                        df_new[['full_name', 'group_name']].to_sql('students', conn, if_exists='append', index=False)
                        st.success("Імпортовано!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Помилка: {e}")

        with t3:
            if st.session_state['role'] in ['admin', 'dean']:
                ids = pd.read_sql("SELECT id, full_name FROM students", conn)
                s_del = st.selectbox("Студент", ids.apply(lambda x: f"{x['id']}: {x['full_name']}", axis=1))
                if st.button("Видалити"):
                    sid = int(s_del.split(":")[0])
                    conn.execute("DELETE FROM students WHERE id=?", (sid,))
                    conn.commit()
                    st.success("Видалено")
                    st.rerun()
