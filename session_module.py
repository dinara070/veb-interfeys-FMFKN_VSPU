import re
import streamlit as st
import pandas as pd
from datetime import datetime

from database import create_connection, log_action, convert_df_to_csv
from config import GROUPS_DATA, SUBJECTS_LIST, DEAN_LEVEL


def session_module_view():
    st.title("Сесія та Рух контингенту")
    if st.session_state['role'] not in DEAN_LEVEL:
        st.error("Доступ заборонено.")
        return

    conn = create_connection()
    c = conn.cursor()

    tab_session, tab_grading, tab_movement = st.tabs([
        "📑 Відомості (Сесія)", "✍️ Внесення оцінок", "🚀 Рух студентів"
    ])

    # --- СТВОРЕННЯ ВІДОМОСТЕЙ ---
    with tab_session:
        st.header("Підготовка екзаменаційних відомостей")
        c1, c2 = st.columns([1, 2])

        with c1:
            with st.form("create_sheet"):
                st.subheader("➕ Створити відомість")
                sheet_num = st.text_input("Номер відомості (№)")
                group_sel = st.selectbox("Група", list(GROUPS_DATA.keys()))
                subj_sel = st.selectbox("Дисципліна", SUBJECTS_LIST)
                control_type = st.selectbox("Тип контролю", [
                    "Екзамен", "Залік", "Диференційований залік", "Перездача", "Комісія"
                ])
                date_exam = st.date_input("Дата проведення")
                examiner = st.text_input("Екзаменатор", value=st.session_state['full_name'])

                if st.form_submit_button("Згенерувати відомість"):
                    if sheet_num:
                        c.execute(
                            "INSERT INTO exam_sheets "
                            "(sheet_number, group_name, subject, control_type, exam_date, examiner, status) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (sheet_num, group_sel, subj_sel, control_type,
                             str(date_exam), examiner, "Відкрита")
                        )
                        conn.commit()
                        st.success(f"Відомість №{sheet_num} створена!")
                        st.rerun()
                    else:
                        st.warning("Вкажіть номер відомості.")

        with c2:
            st.subheader("📂 Журнал відомостей")
            sheets_df = pd.read_sql("SELECT * FROM exam_sheets ORDER BY id DESC", conn)
            st.dataframe(sheets_df, use_container_width=True)
            if not sheets_df.empty:
                st.download_button(
                    "⬇️ Завантажити реєстр відомостей",
                    convert_df_to_csv(sheets_df), "exam_sheets.csv", "text/csv"
                )

    # --- ВНЕСЕННЯ ОЦІНОК ---
    with tab_grading:
        st.header("Занесення оцінок до бази даних")
        st.info("Оцінки, внесені тут, автоматично потрапляють у загальний журнал успішності.")

        sheets = pd.read_sql(
            "SELECT id, sheet_number, group_name, subject, control_type "
            "FROM exam_sheets WHERE status='Відкрита'",
            conn
        )

        if not sheets.empty:
            sheet_options = sheets.apply(
                lambda x: f"№{x['sheet_number']} | {x['group_name']} | {x['subject']} ({x['control_type']})",
                axis=1
            ).tolist()
            selected_sheet_str = st.selectbox("Оберіть активну відомість:", sheet_options)

            sheet_idx = sheet_options.index(selected_sheet_str)
            sel_sheet_data = sheets.iloc[sheet_idx]

            curr_group = sel_sheet_data['group_name']
            curr_subj = sel_sheet_data['subject']
            curr_type = sel_sheet_data['control_type']

            st.markdown(f"**Група:** {curr_group} | **Предмет:** {curr_subj} | **Тип:** {curr_type}")

            students_list = pd.read_sql(
                f"SELECT full_name FROM students WHERE group_name='{curr_group}'", conn
            )['full_name'].tolist()
            existing_grades = pd.read_sql(
                f"SELECT student_name, grade FROM grades "
                f"WHERE group_name='{curr_group}' AND subject='{curr_subj}' AND type_of_work='{curr_type}'",
                conn
            )

            data = []
            for student in students_list:
                found = existing_grades[existing_grades['student_name'] == student]
                grade = found.iloc[0]['grade'] if not found.empty else 0
                data.append({"Студент": student, "Оцінка": grade})

            df_grading = pd.DataFrame(data)
            st.write("Проставте оцінки у таблиці нижче:")

            edited_grades = st.data_editor(
                df_grading, use_container_width=True, key="editor_exam", hide_index=True
            )

            if st.button("💾 Зберегти оцінки в БД", key="save_exam_grades"):
                date_now = str(datetime.now().date())
                count_updated = 0

                for index, row in edited_grades.iterrows():
                    s_name = row['Студент']
                    s_grade = row['Оцінка']

                    check = c.execute(
                        "SELECT id FROM grades WHERE student_name=? AND subject=? AND type_of_work=?",
                        (s_name, curr_subj, curr_type)
                    ).fetchone()

                    if check:
                        c.execute("UPDATE grades SET grade=?, date=? WHERE id=?",
                                  (s_grade, date_now, check[0]))
                    else:
                        c.execute(
                            "INSERT INTO grades (student_name, group_name, subject, type_of_work, grade, date) "
                            "VALUES (?,?,?,?,?,?)",
                            (s_name, curr_group, curr_subj, curr_type, s_grade, date_now)
                        )
                    count_updated += 1

                conn.commit()
                st.success(f"Успішно збережено {count_updated} оцінок!")
                log_action(st.session_state['full_name'], "Exam Grading",
                           f"Внесено оцінки: {curr_group}, {curr_subj}")
                st.rerun()
        else:
            st.warning("Немає відкритих відомостей. Спочатку створіть відомість у першій вкладці.")

    # --- РУХ КОНТИНГЕНТУ ---
    with tab_movement:
        st.header("Переведення на наступний навчальний рік")
        col_move1, col_move2 = st.columns(2)

        with col_move1:
            st.subheader("🔄 Переведення групи (курс +1)")
            move_group = st.selectbox("Оберіть групу", list(GROUPS_DATA.keys()), key="move_grp")

            match = re.match(r"(\d+)(.*)", move_group)
            next_name = move_group
            is_graduating = False

            if match:
                num, rest = int(match.group(1)), match.group(2)
                if num < 4:
                    next_name = f"{num + 1}{rest}"
                else:
                    next_name = f"Випуск-{move_group}"
                    is_graduating = True

            new_group_name = st.text_input("Нова назва групи:", value=next_name)

            if st.button("Виконати переведення"):
                if is_graduating:
                    students = pd.read_sql(
                        f"SELECT full_name FROM students WHERE group_name='{move_group}'", conn
                    )['full_name'].tolist()
                    for s in students:
                        c.execute(
                            "UPDATE student_education_info SET status='Випускник' WHERE student_name=?", (s,)
                        )
                        c.execute("UPDATE students SET group_name=? WHERE full_name=?", (new_group_name, s))
                else:
                    c.execute(
                        "UPDATE students SET group_name=? WHERE group_name=?", (new_group_name, move_group)
                    )

                conn.commit()
                log_action(st.session_state['full_name'], "Group Move",
                           f"{move_group} -> {new_group_name}")
                st.success("Переведення виконано!")
                st.rerun()

        with col_move2:
            st.subheader("🚫 Відрахування / Академвідпустка")
            action_type = st.selectbox("Дія", ["Відрахування", "Академвідпустка"])
            all_students = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
            student_to_action = st.selectbox("Студент", all_students, key="st_action")
            reason_move = st.text_input("Причина / № Наказу")

            if st.button("Застосувати"):
                status_map = {
                    "Відрахування": "Відрахований",
                    "Академвідпустка": "У академвідпустці"
                }
                new_status = status_map[action_type]
                c.execute(
                    "INSERT OR IGNORE INTO student_education_info (student_name) VALUES (?)",
                    (student_to_action,)
                )
                c.execute(
                    "UPDATE student_education_info SET status=? WHERE student_name=?",
                    (new_status, student_to_action)
                )

                if action_type == "Відрахування":
                    c.execute("DELETE FROM students WHERE full_name=?", (student_to_action,))

                conn.commit()
                log_action(st.session_state['full_name'], "Status Change",
                           f"{student_to_action}: {new_status}")
                st.success("Статус змінено!")
                st.rerun()
