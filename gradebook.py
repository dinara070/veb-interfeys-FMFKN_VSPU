import streamlit as st
import pandas as pd
import io

from db import create_connection
from groups_data import GROUPS_DATA
from constants import SUBJECTS_LIST


def gradebook_view():
    st.title("💯 Журнал Оцінок")
    conn = create_connection()
    c = conn.cursor()

    if st.session_state['role'] in ['student', 'starosta']:
        df = pd.read_sql(
            f"SELECT subject, type_of_work, grade, date FROM grades "
            f"WHERE student_name='{st.session_state['full_name']}'",
            conn
        )
        st.dataframe(df, use_container_width=True)
        return

    t_journal, t_ops = st.tabs(["Журнал", "📥/📤 Операції"])

    c1, c2, c3 = st.columns(3)
    grp = c1.selectbox("Група", list(GROUPS_DATA.keys()))

    stds_df = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{grp}'", conn)
    students_in_group = stds_df['full_name'].tolist() if not stds_df.empty else []
    selected_student = c2.selectbox("Студент", ["Всі студенти"] + students_in_group)

    subj = c3.selectbox("Предмет", SUBJECTS_LIST)

    with t_journal:
        with st.expander("➕ Додати колонку"):
            with st.form("new_col"):
                nm = st.text_input("Назва")
                dt = st.date_input("Дата")
                if st.form_submit_button("Створити"):
                    if nm and students_in_group:
                        for s in students_in_group:
                            c.execute(
                                "INSERT INTO grades (student_name, group_name, subject, type_of_work, grade, date) "
                                "VALUES (?,?,?,?,?,?)",
                                (s, grp, subj, nm, 0, str(dt))
                            )
                        conn.commit()
                        st.rerun()
                    else:
                        st.warning("Перевірте назву або наявність студентів у групі.")

        query = (
            f"SELECT student_name, type_of_work, grade FROM grades "
            f"WHERE group_name='{grp}' AND subject='{subj}'"
        )
        if selected_student != "Всі студенти":
            query += f" AND student_name='{selected_student}'"

        raw = pd.read_sql(query, conn)

        if not raw.empty:
            matrix = raw.pivot_table(
                index='student_name', columns='type_of_work', values='grade', aggfunc='first'
            ).fillna(0)

            if st.session_state['role'] == 'tech_admin':
                st.info("ℹ️ Режим перегляду. Збереження недоступне.")
                st.dataframe(matrix, use_container_width=True)
            else:
                edited = st.data_editor(matrix, use_container_width=True)
                if st.button("Зберегти зміни"):
                    for s_name, row in edited.iterrows():
                        for w_name, val in row.items():
                            c.execute(
                                "UPDATE grades SET grade=? WHERE student_name=? AND subject=? AND type_of_work=?",
                                (val, s_name, subj, w_name)
                            )
                    conn.commit()
                    st.success("Дані оновлено!")
        else:
            st.info("Даних немає. Додайте колонку.")

    with t_ops:
        st.subheader("📤 Експорт")
        raw_export = pd.read_sql(
            f"SELECT * FROM grades WHERE group_name='{grp}' AND subject='{subj}'", conn
        )

        col_ex1, col_ex2 = st.columns(2)
        csv_data = raw_export.to_csv(index=False).encode('utf-8-sig')
        col_ex1.download_button("📄 Експорт CSV", csv_data, "grades.csv", "text/csv")

        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                raw_export.to_excel(writer, index=False)
            col_ex2.download_button("📊 Експорт Excel", buffer.getvalue(), "grades.xlsx")
        except Exception:
            col_ex2.info("Excel тимчасово недоступний (використовуйте CSV)")

        st.divider()
        st.subheader("📥 Імпорт")
        up_file = st.file_uploader("Оберіть файл (CSV або XLSX)", type=["csv", "xlsx"])

        if up_file and st.button("🚀 Виконати імпорт"):
            try:
                df_new = (pd.read_csv(up_file) if up_file.name.endswith('.csv')
                          else pd.read_excel(up_file))
                df_new.to_sql('grades', conn, if_exists='append', index=False)
                st.success("Успішно імпортовано!")
                st.rerun()
            except Exception as e:
                st.error(f"Помилка імпорту: {e}")
