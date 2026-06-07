import streamlit as st
import pandas as pd
from datetime import datetime

from db import create_connection, log_action, convert_df_to_csv
from groups_data import GROUPS_DATA
from constants import DEAN_LEVEL


def archive_view():
    st.title("🗂️ Архів Студентів")
    conn = create_connection()
    c = conn.cursor()

    tab_view, tab_add, tab_restore = st.tabs([
        "📋 Переглянути архів", "➕ Архівувати студента", "♻️ Відновити"
    ])

    # ── ПЕРЕГЛЯД АРХІВУ ───────────────────────────────────────────────────
    with tab_view:
        col_f1, col_f2 = st.columns(2)
        reason_filter = col_f1.selectbox(
            "Причина",
            ["Всі", "Відрахування", "Випуск", "Академвідпустка", "Переведення"]
        )
        search_name = col_f2.text_input("🔍 Пошук по ПІБ", placeholder="Введіть прізвище...")

        query = "SELECT * FROM students_archive"
        params = []
        if reason_filter != "Всі":
            query += " WHERE reason=?"
            params.append(reason_filter)
        query += " ORDER BY archive_date DESC"

        arch_df = pd.read_sql(query, conn, params=params)

        if search_name:
            arch_df = arch_df[arch_df['full_name'].str.contains(search_name, case=False, na=False)]

        if not arch_df.empty:
            # KPI
            k1, k2, k3 = st.columns(3)
            k1.metric("📦 В архіві", len(arch_df))
            k2.metric("🎓 Випускників",
                      int((arch_df['reason'] == 'Випуск').sum()))
            k3.metric("❌ Відрахованих",
                      int((arch_df['reason'] == 'Відрахування').sum()))

            st.divider()

            # Стилізована таблиця
            display_df = arch_df[['full_name', 'group_name', 'reason', 'order_number',
                                   'archive_date', 'avg_grade']].copy()
            display_df.columns = ['ПІБ', 'Група', 'Причина', '№ Наказу', 'Дата', 'Серед. бал']

            def color_reason(val):
                colors = {
                    'Відрахування': 'color: #ff4444',
                    'Випуск': 'color: #44bb44',
                    'Академвідпустка': 'color: #ff8800',
                    'Переведення': 'color: #1f77b4'
                }
                return colors.get(val, '')

            st.dataframe(
                display_df.style.map(color_reason, subset=['Причина']),
                use_container_width=True
            )

            st.download_button(
                "⬇️ Завантажити архів (CSV)",
                convert_df_to_csv(arch_df),
                f"students_archive_{datetime.now().date()}.csv",
                "text/csv"
            )
        else:
            st.info("Архів порожній або немає записів за обраними фільтрами.")

    # ── АРХІВУВАННЯ ───────────────────────────────────────────────────────
    with tab_add:
        if st.session_state.get('role') not in DEAN_LEVEL:
            st.error("Доступ заборонено.")
            return

        st.info("Оберіть студента для переміщення в архів. Студент буде видалений зі списку активних.")

        col1, col2 = st.columns(2)
        with col1:
            all_students_df = pd.read_sql(
                "SELECT full_name, group_name FROM students ORDER BY group_name, full_name", conn
            )
            if all_students_df.empty:
                st.warning("Немає активних студентів.")
            else:
                student_options = all_students_df.apply(
                    lambda x: f"{x['full_name']} ({x['group_name']})", axis=1
                ).tolist()
                selected = st.selectbox("Студент", student_options)
                selected_name = selected.split(" (")[0]
                selected_group = selected.split("(")[1].rstrip(")")

        with col2:
            reason = st.selectbox("Причина архівування", [
                "Відрахування", "Випуск", "Академвідпустка", "Переведення"
            ])
            order_num = st.text_input("№ Наказу / Підстава", placeholder="Напр. №123-В від 01.06.2025")
            archive_date = st.date_input("Дата", value=datetime.now().date())

        st.divider()

        if not all_students_df.empty:
            # Показуємо статистику студента
            avg_q = pd.read_sql(
                f"SELECT AVG(grade) as avg FROM grades WHERE student_name='{selected_name}'", conn
            )
            avg_grade = round(float(avg_q.iloc[0, 0]), 2) if avg_q.iloc[0, 0] else 0.0

            col_info1, col_info2 = st.columns(2)
            col_info1.metric("Студент", selected_name)
            col_info2.metric("Середній бал", avg_grade)

            confirmed = st.checkbox(
                f"✅ Підтверджую архівування: **{selected_name}** — **{reason}**"
            )
            if st.button("🗂️ Архівувати студента", type="primary", disabled=not confirmed):
                # Записуємо в архів
                c.execute(
                    "INSERT INTO students_archive "
                    "(full_name, group_name, reason, order_number, archive_date, archived_by, avg_grade) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (selected_name, selected_group, reason, order_num,
                     str(archive_date), st.session_state['full_name'], avg_grade)
                )
                # Видаляємо з активних
                c.execute("DELETE FROM students WHERE full_name=?", (selected_name,))
                conn.commit()
                log_action(
                    st.session_state['full_name'], "Archive Student",
                    f"{selected_name} → {reason} (наказ {order_num})"
                )
                st.success(f"✅ {selected_name} переміщено в архів ({reason}).")
                st.rerun()

    # ── ВІДНОВЛЕННЯ ────────────────────────────────────────────────────────
    with tab_restore:
        if st.session_state.get('role') not in DEAN_LEVEL:
            st.error("Доступ заборонено.")
            return

        st.info("Відновлення повертає студента до списку активних (крім випускників).")

        restore_df = pd.read_sql(
            "SELECT id, full_name, group_name, reason FROM students_archive "
            "WHERE reason != 'Випуск' ORDER BY archive_date DESC",
            conn
        )

        if restore_df.empty:
            st.success("Немає студентів для відновлення.")
        else:
            restore_options = restore_df.apply(
                lambda x: f"[ID:{x['id']}] {x['full_name']} ({x['group_name']}) — {x['reason']}",
                axis=1
            ).tolist()
            selected_restore = st.selectbox("Оберіть студента для відновлення", restore_options)
            restore_id = int(selected_restore.split("]")[0].replace("[ID:", ""))

            restore_row = restore_df[restore_df['id'] == restore_id].iloc[0]

            groups_list = list(GROUPS_DATA.keys())
            default_idx = groups_list.index(restore_row['group_name']) \
                if restore_row['group_name'] in groups_list else 0
            new_group = st.selectbox("Повернути до групи", groups_list, index=default_idx)

            if st.button("♻️ Відновити студента", type="primary"):
                # Повертаємо в активних
                c.execute(
                    "INSERT INTO students (full_name, group_name) VALUES (?,?)",
                    (restore_row['full_name'], new_group)
                )
                # Видаляємо з архіву
                c.execute("DELETE FROM students_archive WHERE id=?", (restore_id,))
                conn.commit()
                log_action(
                    st.session_state['full_name'], "Restore Student",
                    f"{restore_row['full_name']} повернуто до {new_group}"
                )
                st.success(f"✅ {restore_row['full_name']} відновлено у групі {new_group}!")
                st.rerun()
