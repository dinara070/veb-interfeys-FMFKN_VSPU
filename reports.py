import streamlit as st
import pandas as pd
import io

from db import create_connection
from groups_data import GROUPS_DATA
from constants import SUBJECTS_LIST


def reports_view():
    st.title("📊 Звіти та Пошук")
    conn = create_connection()

    t1, t2, t3 = st.tabs(["📋 Відомість (Група/Предмет)", "🎓 Картка Студента", "📈 Зведена відомість"])

    with t1:
        st.subheader("Формування відомості")
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Група", list(GROUPS_DATA.keys()), key="rep_grp")
        subj = c2.selectbox("Предмет", SUBJECTS_LIST, key="rep_subj")

        raw = pd.read_sql(
            f"SELECT student_name, type_of_work, grade FROM grades "
            f"WHERE group_name='{grp}' AND subject='{subj}'",
            conn
        )

        if not raw.empty:
            matrix = raw.pivot_table(
                index='student_name', columns='type_of_work', values='grade', aggfunc='first'
            ).fillna(0)
            st.dataframe(matrix, use_container_width=True)

            st.markdown("#### Експорт відомості")
            ex_c1, ex_c2, ex_c3 = st.columns(3)

            ex_c1.download_button(
                "⬇️ CSV", matrix.to_csv().encode('utf-8-sig'),
                f"vidomist_{grp}_{subj}.csv", "text/csv"
            )

            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    matrix.to_excel(writer, sheet_name='Відомість')
                ex_c2.download_button("📊 Excel", buf.getvalue(),
                                      f"vidomist_{grp}_{subj}.xlsx", "application/vnd.ms-excel")
            except Exception:
                ex_c2.info("Excel двигун не знайдено")

            ex_c3.download_button(
                "📜 JSON", matrix.to_json(force_ascii=False),
                f"vidomist_{grp}_{subj}.json", "application/json"
            )
        else:
            st.warning("Наразі дані не завантажені.")

    with t2:
        st.subheader("Електронна Анкета Студента")
        all_students = pd.read_sql("SELECT full_name FROM students", conn)
        if not all_students.empty:
            selected_student = st.selectbox("Оберіть студента", all_students['full_name'].tolist())

            if st.button("📤 Експортувати всі дані студента (JSON)"):
                student_full_data = {
                    "main": pd.read_sql(
                        f"SELECT * FROM students WHERE full_name='{selected_student}'", conn
                    ).to_dict('records'),
                    "grades": pd.read_sql(
                        f"SELECT * FROM grades WHERE student_name='{selected_student}'", conn
                    ).to_dict('records')
                }
                st.download_button(
                    "Завантажити JSON анкету",
                    str(student_full_data),
                    f"anketa_{selected_student}.json"
                )

            tab_main, tab_grades = st.tabs(["Загальна", "Успішність"])

            with tab_main:
                student_row = pd.read_sql(
                    f"SELECT * FROM students WHERE full_name='{selected_student}'", conn
                )
                st.dataframe(student_row, use_container_width=True)

            with tab_grades:
                grades = pd.read_sql(
                    f"SELECT subject, type_of_work, grade, date FROM grades "
                    f"WHERE student_name='{selected_student}'",
                    conn
                )
                if not grades.empty:
                    st.dataframe(grades, use_container_width=True)
                    st.metric("Середній бал", f"{grades['grade'].mean():.2f}")
                else:
                    st.info("Оцінок немає.")
        else:
            st.error("Наразі дані не завантажені.")

    with t3:
        st.subheader("Генератор Зведеної Відомості")

        try:
            db_groups = pd.read_sql("SELECT DISTINCT group_name FROM students", conn)['group_name'].tolist()
        except Exception:
            db_groups = list(GROUPS_DATA.keys())

        grp_sum = st.selectbox("Оберіть групу", db_groups, key="rep_sum_grp")

        with st.expander("📥 Імпорт даних у зведену відомість"):
            up_file = st.file_uploader("Завантажте CSV або Excel", type=['csv', 'xlsx'], key="import_sum")
            if up_file and st.button("🚀 Виконати імпорт"):
                try:
                    df_imp = (pd.read_csv(up_file) if up_file.name.endswith('.csv')
                              else pd.read_excel(up_file))
                    df_imp.to_sql('grades', conn, if_exists='append', index=False)
                    st.success("Дані успішно імпортовані!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Помилка імпорту: {e}")

        try:
            available_subjects = pd.read_sql(
                f"SELECT DISTINCT subject FROM grades WHERE group_name='{grp_sum}'", conn
            )['subject'].tolist()
        except Exception:
            available_subjects = []

        if not available_subjects:
            available_subjects = SUBJECTS_LIST

        selected_subjects = st.multiselect(
            "Оберіть предмети для відомості",
            options=available_subjects,
            default=available_subjects[:5] if len(available_subjects) > 5 else available_subjects
        )

        if st.button("🔄 Згенерувати таблицю"):
            if selected_subjects:
                try:
                    subjects_placeholder = ",".join(["?"] * len(selected_subjects))
                    query = f"""
                        SELECT student_name, subject, AVG(grade) as final_grade
                        FROM grades
                        WHERE group_name = ? AND subject IN ({subjects_placeholder})
                        GROUP BY student_name, subject
                    """
                    params = [grp_sum] + selected_subjects
                    data = pd.read_sql(query, conn, params=params)

                    if not data.empty:
                        summary_matrix = (
                            data.pivot_table(index='student_name', columns='subject', values='final_grade')
                            .fillna(0).round(0).astype(int)
                        )
                        all_students_df = pd.read_sql(
                            "SELECT full_name FROM students WHERE group_name=?", conn, params=[grp_sum]
                        )
                        summary_matrix = (
                            all_students_df
                            .merge(summary_matrix, left_on='full_name', right_index=True, how='left')
                            .fillna(0)
                        )
                        summary_matrix.set_index('full_name', inplace=True)

                        st.success(f"Згенеровано відомість для групи {grp_sum}")
                        st.dataframe(summary_matrix, use_container_width=True)

                        c_sum1, c_sum2 = st.columns(2)
                        csv_out = summary_matrix.to_csv().encode('utf-8-sig')
                        c_sum1.download_button("⬇️ Експорт CSV", csv_out, f"zvedena_{grp_sum}.csv")

                        try:
                            buf_sum = io.BytesIO()
                            with pd.ExcelWriter(buf_sum, engine='xlsxwriter') as writer:
                                summary_matrix.to_excel(writer)
                            c_sum2.download_button("📊 Експорт Excel", buf_sum.getvalue(),
                                                   f"zvedena_{grp_sum}.xlsx")
                        except Exception:
                            c_sum2.warning("Для Excel потрібна бібліотека xlsxwriter")
                    else:
                        st.warning("В базі даних не знайдено оцінок для вибраних предметів.")
                except Exception as e:
                    st.error(f"Помилка бази даних: {e}")
            else:
                st.error("Будь ласка, оберіть хоча б один предмет.")
