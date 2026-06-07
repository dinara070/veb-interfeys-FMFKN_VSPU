import streamlit as st
import pandas as pd
from datetime import datetime

from db import create_connection, convert_df_to_csv
from constants import SUBJECTS_LIST, DEAN_LEVEL


def deanery_modules_view():
    st.title("Модулі Деканату")
    if st.session_state['role'] not in DEAN_LEVEL:
        st.error("У вас немає доступу до цієї панелі.")
        return

    conn = create_connection()
    c = conn.cursor()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔄 ЄДЕБО", "🛏️ Гуртожиток", "💰 Стипендія",
        "📜 Академ. Довідки", "📝 Інд. Відомості", "📄 Контракти"
    ])

    # --- ЄДЕБО ---
    with tab1:
        st.header("Єдина державна електронна база з питань освіти")
        col_ex, col_im = st.columns(2)

        with col_ex:
            st.subheader("📤 Експорт даних")
            format_type = st.radio("Формат експорту:", ["JSON", "XML (Beta)"])
            if st.button("Згенерувати файл для ЄДЕБО"):
                df_edebo = pd.read_sql(
                    "SELECT s.full_name, s.group_name, u.role FROM students s "
                    "LEFT JOIN users u ON s.full_name = u.full_name",
                    conn
                )
                if format_type == "JSON":
                    json_data = df_edebo.to_json(orient='records', force_ascii=False)
                    st.download_button("⬇️ Завантажити JSON", json_data,
                                       f"edebo_export_{datetime.now().date()}.json", "application/json")
                else:
                    csv_data = df_edebo.to_csv(index=False)
                    st.download_button("⬇️ Завантажити XML/CSV", csv_data,
                                       f"edebo_export_{datetime.now().date()}.csv", "text/csv")

        with col_im:
            st.subheader("📥 Імпорт наказів")
            uploaded_edebo = st.file_uploader("Завантажте файл з ЄДЕБО (JSON/XML)", type=['json', 'xml'])
            if uploaded_edebo:
                st.success("Файл проаналізовано.")

    # --- ГУРТОЖИТОК ---
    with tab2:
        st.header("Управління поселенням")
        c1, c2 = st.columns([1, 2])

        with c1:
            with st.form("dorm_assign"):
                st.subheader("🏠 Поселення")
                all_students = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                student = st.selectbox("Студент", all_students)
                room = st.text_input("Номер кімнати", placeholder="Напр. 405-Б")
                paid = st.checkbox("Оплата за семестр внесена?")
                comment = st.text_area("Примітка (стан кімнати/інвентар)")

                if st.form_submit_button("Зберегти"):
                    status = "Оплачено" if paid else "Борг"
                    exists = c.execute("SELECT id FROM dormitory WHERE student_name=?", (student,)).fetchone()
                    if exists:
                        c.execute(
                            "UPDATE dormitory SET room_number=?, payment_status=?, comments=? WHERE student_name=?",
                            (room, status, comment, student)
                        )
                        st.info("Дані оновлено!")
                    else:
                        c.execute(
                            "INSERT INTO dormitory (student_name, room_number, payment_status, comments) VALUES (?,?,?,?)",
                            (student, room, status, comment)
                        )
                        st.success("Студента поселено!")
                    conn.commit()
                    st.rerun()

        with c2:
            st.subheader("📋 Списки мешканців")
            dorm_df = pd.read_sql("SELECT * FROM dormitory", conn)
            if not dorm_df.empty:
                def highlight_debt(val):
                    color = '#ff4b4b' if val == 'Борг' else '#00cc66'
                    return f'color: {color}'
                st.dataframe(dorm_df.style.map(highlight_debt, subset=['payment_status']),
                             use_container_width=True)
            else:
                st.info("У гуртожитку поки ніхто не живе.")

    # --- СТИПЕНДІЯ ---
    with tab3:
        st.header("Стипендіальна комісія")
        st.markdown("#### 📊 Автоматичний розрахунок рейтингу")
        if st.button("Оновити рейтинг успішності"):
            rating_df = pd.read_sql(
                "SELECT student_name, AVG(grade) as avg_score FROM grades "
                "GROUP BY student_name HAVING avg_score >= 4.0 ORDER BY avg_score DESC",
                conn
            )
            st.dataframe(rating_df, use_container_width=True)
            st.caption("*Показані студенти з балом 4.0 і вище")

        st.divider()
        col_schol1, col_schol2 = st.columns(2)

        with col_schol1:
            with st.form("add_scholarship"):
                st.subheader("Призначення стипендії")
                st_list = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                sch_student = st.selectbox("Студент", st_list, key="sch_st")
                sch_type = st.selectbox("Тип", [
                    "Академічна (Звичайна)", "Академічна (Підвищена)",
                    "Соціальна", "Президентська"
                ])
                sch_amount = st.number_input("Сума (грн)", value=2000, step=100)
                if st.form_submit_button("Призначити"):
                    c.execute(
                        "INSERT INTO scholarship (student_name, type, amount, status, date_assigned) VALUES (?,?,?,?,?)",
                        (sch_student, sch_type, sch_amount, "Активна", datetime.now().strftime("%Y-%m-%d"))
                    )
                    conn.commit()
                    st.success("Стипендію призначено!")
                    st.rerun()

        with col_schol2:
            st.subheader("💰 Активні стипендіати")
            sch_df = pd.read_sql(
                "SELECT student_name, type, amount, status, date_assigned FROM scholarship", conn
            )
            if not sch_df.empty:
                st.dataframe(sch_df, use_container_width=True)
                total_budget = sch_df[sch_df['status'] == 'Активна']['amount'].sum()
                st.metric("Місячний фонд стипендій", f"{total_budget} грн")
            else:
                st.info("Стипендій не призначено.")

    # --- АКАДЕМІЧНІ ДОВІДКИ ---
    with tab4:
        st.header("Академічні довідки (Переведення)")
        st.info("Реєстрація довідок від студентів, що перевелися з інших ЗВО.")
        c_acad1, c_acad2 = st.columns(2)

        with c_acad1:
            with st.form("new_acad_cert"):
                st.subheader("➕ Нова довідка")
                st_list_a = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_name = st.selectbox("Студент", st_list_a)
                cert_num = st.text_input("Номер довідки")
                issue_dt = st.date_input("Дата видачі")
                source = st.text_input("Звідки видана (ЗВО/Факультет)")
                notes = st.text_area("Деталі (кредити, предмети)")
                if st.form_submit_button("Зареєструвати довідку"):
                    c.execute(
                        "INSERT INTO academic_certificates "
                        "(student_name, cert_number, issue_date, source_institution, notes, added_by, added_date) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (s_name, cert_num, str(issue_dt), source, notes,
                         st.session_state['full_name'], str(datetime.now().date()))
                    )
                    conn.commit()
                    st.success("Довідку додано!")
                    st.rerun()

        with c_acad2:
            st.subheader("🗂️ Реєстр довідок")
            df_certs = pd.read_sql("SELECT * FROM academic_certificates", conn)
            st.dataframe(df_certs, use_container_width=True)

    # --- ІНДИВІДУАЛЬНІ ВІДОМОСТІ ---
    with tab5:
        st.header("Індивідуальні відомості")
        c_ind1, c_ind2 = st.columns(2)

        with c_ind1:
            with st.form("new_ind_statement"):
                st.subheader("📄 Створити відомість")
                st_list_i = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_ind = st.selectbox("Студент", st_list_i)
                subj_ind = st.selectbox("Дисципліна", SUBJECTS_LIST)
                type_ind = st.selectbox("Тип відомості", [
                    "На підвищення оцінки", "Академічна різниця",
                    "Індивідуальний графік", "Атестаційний лист екстерна", "Позапланова дисципліна"
                ])
                reason = st.text_input("Підстава (№ розпорядження/заяви)")
                if st.form_submit_button("Сформувати"):
                    c.execute(
                        "INSERT INTO individual_statements "
                        "(student_name, subject, statement_type, reason, date_issued, status, created_by) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (s_ind, subj_ind, type_ind, reason,
                         str(datetime.now().date()), "Активна", st.session_state['full_name'])
                    )
                    conn.commit()
                    st.success(f"Відомість '{type_ind}' створено!")
                    st.rerun()

        with c_ind2:
            st.subheader("🗃️ Активні індивідуальні відомості")
            df_inds = pd.read_sql("SELECT * FROM individual_statements", conn)
            st.dataframe(df_inds, use_container_width=True)

    # --- КОНТРАКТИ ---
    with tab6:
        st.header("Управління контрактами")
        col_con1, col_con2 = st.columns([1, 2])

        with col_con1:
            with st.form("contract_form"):
                st.subheader("📝 Дані договору")
                st_list_c = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_contract = st.selectbox("Студент", st_list_c)
                c_num = st.text_input("Номер договору")
                cd1, cd2 = st.columns(2)
                d_sign = cd1.date_input("Дата підписання")
                d_end = cd2.date_input("Термін дії до")
                cm1, cm2 = st.columns(2)
                amount_total = cm1.number_input("Загальна вартість (грн)", min_value=0.0, step=100.0)
                amount_paid = cm2.number_input("Сплачено (грн)", min_value=0.0, step=100.0)
                notes_c = st.text_area("Умови оплати / Примітки")

                calc_debt = amount_total - amount_paid
                if amount_paid == 0:
                    status_c = "Не оплачено"
                elif calc_debt <= 0:
                    status_c = "Сплачено повністю"
                else:
                    status_c = f"Борг: {calc_debt} грн"

                if st.form_submit_button("Зберегти контракт"):
                    exists_c = c.execute(
                        "SELECT id FROM student_contracts WHERE student_name=? AND contract_number=?",
                        (s_contract, c_num)
                    ).fetchone()
                    if exists_c:
                        c.execute(
                            "UPDATE student_contracts SET date_signed=?, end_date=?, total_amount=?, "
                            "paid_amount=?, payment_status=?, notes=? WHERE id=?",
                            (str(d_sign), str(d_end), amount_total, amount_paid, status_c, notes_c, exists_c[0])
                        )
                        st.success("Дані контракту оновлено!")
                    else:
                        c.execute(
                            "INSERT INTO student_contracts "
                            "(student_name, contract_number, date_signed, end_date, "
                            "total_amount, paid_amount, payment_status, notes) VALUES (?,?,?,?,?,?,?,?)",
                            (s_contract, c_num, str(d_sign), str(d_end),
                             amount_total, amount_paid, status_c, notes_c)
                        )
                        st.success("Новий контракт зареєстровано!")
                    conn.commit()
                    st.rerun()

        with col_con2:
            st.subheader("📂 Реєстр договорів")
            debt_sum = c.execute(
                "SELECT SUM(total_amount - paid_amount) FROM student_contracts WHERE total_amount > paid_amount"
            ).fetchone()[0] or 0
            st.metric("Загальна заборгованість по факультету", f"{debt_sum:,.2f} грн")

            df_contracts = pd.read_sql("SELECT * FROM student_contracts", conn)
            if not df_contracts.empty:
                def highlight_debt_contract(val):
                    if isinstance(val, str) and "Борг" in val:
                        return 'color: #ff4b4b; font-weight: bold'
                    elif isinstance(val, str) and "Не оплачено" in val:
                        return 'color: #ff4b4b'
                    return 'color: #00cc66'
                st.dataframe(
                    df_contracts.style.map(highlight_debt_contract, subset=['payment_status']),
                    use_container_width=True
                )
                st.download_button(
                    "⬇️ Завантажити реєстр (CSV)",
                    convert_df_to_csv(df_contracts),
                    "contracts_registry.csv", "text/csv"
                )
            else:
                st.info("Контрактів ще не додано.")
