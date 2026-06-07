import streamlit as st
import pandas as pd
import io

from db import create_connection
from groups_data import GROUPS_DATA
from constants import SUBJECTS_LIST


def attendance_view():
    st.title("📝 Журнал Відвідуваності")
    conn = create_connection()

    if st.session_state['role'] == 'student':
        df_att = pd.read_sql(
            f"SELECT subject as 'Предмет', date_column as 'Дата', status as 'Статус' "
            f"FROM attendance WHERE student_name='{st.session_state['full_name']}'",
            conn
        )
        st.dataframe(df_att, use_container_width=True)
        return

    c1, c2 = st.columns(2)
    grp = c1.selectbox("Група", list(GROUPS_DATA.keys()), key="att_grp")
    subj = c2.selectbox("Предмет", SUBJECTS_LIST, key="att_sbj")

    col_add, col_imp = st.columns(2)

    with col_add:
        with st.expander("➕ Додати дату вручну"):
            with st.form("new_att_col"):
                col_name = st.text_input("Назва дати (напр. 25.12)")

                stds_in_grp = pd.read_sql(
                    f"SELECT full_name FROM students WHERE group_name='{grp}'", conn
                )['full_name'].tolist()

                student_selection = st.selectbox("Для кого додати:", ["Усі студенти"] + stds_in_grp)
                default_status = st.selectbox("Статус за замовчуванням:", ["", "присутній", "н", "н/п", "з"])

                if st.form_submit_button("Створити"):
                    if col_name:
                        targets = stds_in_grp if student_selection == "Усі студенти" else [student_selection]
                        for s in targets:
                            exists = conn.execute(
                                "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?",
                                (s, subj, col_name)
                            ).fetchone()
                            if not exists:
                                conn.execute(
                                    "INSERT INTO attendance (student_name, group_name, subject, date_column, status) "
                                    "VALUES (?,?,?,?,?)",
                                    (s, grp, subj, col_name, default_status)
                                )
                        conn.commit()
                        st.success(f"Записи для '{col_name}' успішно створено!")
                        st.rerun()
                    else:
                        st.error("Будь ласка, введіть назву дати!")

    with col_imp:
        with st.expander("📥 Імпорт з Excel"):
            uploaded_file = st.file_uploader("Завантажте файл .xlsx", type="xlsx")
            if uploaded_file:
                imp_df = pd.read_excel(uploaded_file, index_col=0)
                if st.button("Підтвердити імпорт"):
                    for s_name, row in imp_df.iterrows():
                        for d_col, val in row.items():
                            val = str(val) if pd.notna(val) else ""
                            res = conn.execute(
                                "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?",
                                (s_name, subj, d_col)
                            ).fetchone()
                            if res:
                                conn.execute("UPDATE attendance SET status=? WHERE id=?", (val, res[0]))
                            else:
                                conn.execute(
                                    "INSERT INTO attendance (student_name, group_name, subject, date_column, status) "
                                    "VALUES (?,?,?,?,?)",
                                    (s_name, grp, subj, d_col, val)
                                )
                    conn.commit()
                    st.success("Дані з файлу успішно імпортовано!")
                    st.rerun()

    raw = pd.read_sql(
        f"SELECT student_name, date_column, status FROM attendance "
        f"WHERE group_name='{grp}' AND subject='{subj}'",
        conn
    )

    if not raw.empty:
        matrix = raw.pivot_table(
            index='student_name', columns='date_column', values='status', aggfunc='first'
        ).fillna("")

        st.divider()
        f_col1, f_col2 = st.columns([2, 1])

        with f_col1:
            missed_counts = (matrix == "н").sum(axis=1)
            max_misses = int(missed_counts.max()) if not missed_counts.empty else 0
            n_filter = st.slider("🔍 Фільтр прогульників: Студенти з 'н' >= N:", 0, max_misses, 0)

        with f_col2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                matrix.to_excel(writer, sheet_name='Відвідуваність')
            st.write("📫 Звітність")
            st.download_button(
                label="📥 Завантажити Excel",
                data=buffer.getvalue(),
                file_name=f"Attendance_{grp}_{subj}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        filtered_matrix = matrix[missed_counts >= n_filter]

        column_config = {
            col: st.column_config.SelectboxColumn(
                col, options=["", "присутній", "н", "н/п", "з"], width="small"
            ) for col in filtered_matrix.columns
        }

        st.write(f"### 📋 Журнал: {grp} — {subj}")
        st.info("💡 Ви можете змінювати статуси прямо в таблиці та натиснути кнопку 'Зберегти' внизу.")

        edited = st.data_editor(filtered_matrix, column_config=column_config, use_container_width=True)

        if st.button("💾 Зберегти зміни у журналі"):
            for s_name, row in edited.iterrows():
                for d_col, val in row.items():
                    db_res = conn.execute(
                        "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?",
                        (s_name, subj, d_col)
                    ).fetchone()
                    if db_res:
                        conn.execute("UPDATE attendance SET status=? WHERE id=?", (val, db_res[0]))
            conn.commit()
            st.success("Усі зміни успішно записані в базу даних!")
            st.rerun()
    else:
        st.info("У журналі поки немає даних для обраної групи та предмета.")
