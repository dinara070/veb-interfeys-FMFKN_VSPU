import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

from db import create_connection, log_action
from groups_data import GROUPS_DATA
from constants import SUBJECTS_LIST, DEAN_LEVEL


def _build_pdf_html(content: str, title: str) -> str:
    """Генерує HTML-шаблон для подальшого конвертування або завантаження."""
    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Times New Roman', serif; margin: 40px; font-size: 12pt; }}
  .header {{ text-align: center; margin-bottom: 30px; }}
  .university {{ font-size: 11pt; color: #333; }}
  .doc-title {{ font-size: 16pt; font-weight: bold; margin: 20px 0 10px; }}
  .doc-subtitle {{ font-size: 12pt; color: #555; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  th {{ background: #2c3e50; color: white; padding: 8px; text-align: left; }}
  td {{ padding: 6px 8px; border: 1px solid #ccc; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .footer {{ margin-top: 40px; font-size: 10pt; color: #777; text-align: right; }}
  .signature {{ margin-top: 60px; display: flex; justify-content: space-between; }}
  .sig-line {{ border-top: 1px solid #333; width: 200px; text-align: center;
               padding-top: 4px; font-size: 10pt; color: #555; }}
  .seal {{ text-align: center; color: #777; font-size: 10pt; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <div class="university">Вінницький державний педагогічний університет імені Михайла Коцюбинського</div>
  <div class="university">Факультет математики, фізики і комп'ютерних наук</div>
  <div class="doc-title">{title}</div>
  <div class="doc-subtitle">Дата видачі: {datetime.now().strftime('%d.%m.%Y')}</div>
</div>
{content}
<div class="footer">
  Документ сформовано автоматично системою «Project Deanery» — {datetime.now().strftime('%d.%m.%Y %H:%M')}
</div>
<div class="signature">
  <div class="sig-line">Декан факультету</div>
  <div class="seal">М.П.</div>
  <div class="sig-line">Секретар деканату</div>
</div>
</body>
</html>"""


def pdf_generator_view():
    st.title("🖨️ Генерація Документів")
    conn = create_connection()

    doc_type = st.selectbox("📄 Оберіть тип документу", [
        "📋 Довідка про навчання",
        "📊 Відомість успішності групи",
        "🎓 Виписка оцінок студента (Transcript)",
        "🏠 Список мешканців гуртожитку",
        "💰 Відомість стипендіатів",
        "👥 Списковий склад групи",
    ])

    st.divider()

    # ── ДОВІДКА ПРО НАВЧАННЯ ──────────────────────────────────────────────
    if doc_type == "📋 Довідка про навчання":
        all_students = pd.read_sql(
            "SELECT s.full_name, s.group_name FROM students s ORDER BY s.full_name", conn
        )
        if all_students.empty:
            st.warning("Немає студентів у базі.")
            return

        col1, col2 = st.columns(2)
        student = col1.selectbox("Студент", all_students['full_name'].tolist())
        purpose = col2.text_input("Призначення довідки", placeholder="Напр. за місцем вимоги")

        row = all_students[all_students['full_name'] == student].iloc[0]

        # Визначаємо курс з назви групи
        course_map = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}
        course_digit = row['group_name'][0] if row['group_name'] else '?'
        course_roman = course_map.get(course_digit, course_digit)

        # Спеціальність з назви групи
        spec_map = {'СОМ': 'Середня освіта (Математика)', 'СОІ': 'Середня освіта (Інформатика)',
                    'М': 'Математика', 'СОФА': 'Середня освіта (Фізика та Астрономія)',
                    'ММ': 'Математика (магістр)', 'МСОМ': 'Середня освіта (Математика, магістр)',
                    'МСОІ': 'Середня освіта (Інформатика, магістр)',
                    'МСОФА': 'Середня освіта (Фізика та Астрономія, магістр)'}
        spec_key = row['group_name'].lstrip('1234')
        specialty = spec_map.get(spec_key, 'Інша')

        preview_html = f"""
        <div style="border: 1px solid #ccc; padding: 20px; font-family: serif;">
            <p>Видана <b>{student}</b>, що дійсно є студентом <b>{course_roman} курсу</b>
            денної форми навчання спеціальності <b>{specialty}</b> (група <b>{row['group_name']}</b>).</p>
            <p>Довідка видана для надання {purpose or 'за місцем вимоги'}.</p>
        </div>"""

        st.markdown("**Попередній перегляд:**")
        st.markdown(preview_html, unsafe_allow_html=True)

        if st.button("📥 Завантажити HTML-документ", type="primary"):
            content = f"""
            <p>Видана <b>{student}</b>, що дійсно є студентом <b>{course_roman} курсу</b>
            денної форми навчання спеціальності <b>{specialty}</b>
            (група <b>{row['group_name']}</b>).</p>
            <p>Довідка видана для надання {purpose or 'за місцем вимоги'}.</p>
            <p>Дійсна за наявності підпису та печатки.</p>"""
            html = _build_pdf_html(content, "ДОВІДКА ПРО НАВЧАННЯ")
            st.download_button(
                "⬇️ Зберегти довідку (.html)",
                html.encode('utf-8'),
                f"dovidka_{student.replace(' ', '_')}.html",
                "text/html"
            )
            log_action(st.session_state.get('full_name', ''), "Generate Doc",
                       f"Довідка: {student}")

    # ── ВІДОМІСТЬ УСПІШНОСТІ ──────────────────────────────────────────────
    elif doc_type == "📊 Відомість успішності групи":
        col1, col2 = st.columns(2)
        group = col1.selectbox("Група", list(GROUPS_DATA.keys()))
        subject = col2.selectbox("Предмет", SUBJECTS_LIST)

        raw = pd.read_sql(
            f"SELECT student_name, type_of_work, grade FROM grades "
            f"WHERE group_name='{group}' AND subject='{subject}'", conn
        )

        if raw.empty:
            st.warning("Немає даних оцінок для обраної групи та предмету.")
        else:
            matrix = raw.pivot_table(
                index='student_name', columns='type_of_work', values='grade', aggfunc='first'
            ).fillna(0).astype(int)
            matrix['Середній'] = raw.groupby('student_name')['grade'].mean().round(1)
            st.dataframe(matrix, use_container_width=True)

            if st.button("📥 Завантажити відомість (.html)", type="primary"):
                table_rows = "".join(
                    f"<tr><td>{i+1}</td><td>{name}</td>" +
                    "".join(f"<td style='text-align:center'>{matrix.loc[name, col]}</td>"
                            for col in matrix.columns) + "</tr>"
                    for i, name in enumerate(matrix.index)
                )
                headers = "<th>№</th><th>ПІБ студента</th>" + \
                          "".join(f"<th>{col}</th>" for col in matrix.columns)
                content = f"""
                <p><b>Група:</b> {group} &nbsp;&nbsp; <b>Дисципліна:</b> {subject}</p>
                <table><tr>{headers}</tr>{table_rows}</table>"""
                html = _build_pdf_html(content, f"ВІДОМІСТЬ УСПІШНОСТІ — {group}")
                st.download_button(
                    "⬇️ Зберегти (.html)",
                    html.encode('utf-8'),
                    f"vidomist_{group}_{subject[:20]}.html",
                    "text/html"
                )

    # ── ВИПИСКА ОЦІНОК СТУДЕНТА ───────────────────────────────────────────
    elif doc_type == "🎓 Виписка оцінок студента (Transcript)":
        all_students = pd.read_sql("SELECT full_name FROM students ORDER BY full_name", conn)[
            'full_name'].tolist()
        student = st.selectbox("Студент", all_students)

        grades = pd.read_sql(
            f"SELECT subject, type_of_work, grade, date FROM grades "
            f"WHERE student_name='{student}' ORDER BY subject",
            conn
        )

        if grades.empty:
            st.warning("Немає оцінок для цього студента.")
        else:
            avg = grades['grade'].mean()
            col1, col2 = st.columns(2)
            col1.metric("Середній бал", f"{avg:.2f}")
            col2.metric("Записів", len(grades))
            st.dataframe(grades, use_container_width=True)

            if st.button("📥 Завантажити Transcript (.html)", type="primary"):
                rows = "".join(
                    f"<tr><td>{r['subject']}</td><td>{r['type_of_work']}</td>"
                    f"<td style='text-align:center'><b>{r['grade']}</b></td><td>{r['date']}</td></tr>"
                    for _, r in grades.iterrows()
                )
                content = f"""
                <p><b>Студент:</b> {student}</p>
                <p><b>Середній бал:</b> {avg:.2f}</p>
                <table>
                  <tr><th>Дисципліна</th><th>Тип роботи</th><th>Оцінка</th><th>Дата</th></tr>
                  {rows}
                </table>"""
                html = _build_pdf_html(content, "АКАДЕМІЧНА ВИПИСКА (TRANSCRIPT)")
                st.download_button(
                    "⬇️ Зберегти (.html)",
                    html.encode('utf-8'),
                    f"transcript_{student.replace(' ','_')}.html",
                    "text/html"
                )

    # ── СПИСОК МЕШКАНЦІВ ГУРТОЖИТКУ ───────────────────────────────────────
    elif doc_type == "🏠 Список мешканців гуртожитку":
        dorm_df = pd.read_sql("SELECT * FROM dormitory ORDER BY room_number", conn)
        if dorm_df.empty:
            st.warning("Гуртожиток порожній.")
        else:
            st.dataframe(dorm_df, use_container_width=True)
            if st.button("📥 Завантажити список (.html)", type="primary"):
                rows = "".join(
                    f"<tr><td>{r['room_number']}</td><td>{r['student_name']}</td>"
                    f"<td style='color:{'green' if r['payment_status']=='Оплачено' else 'red'}'>"
                    f"{r['payment_status']}</td><td>{r['comments'] or ''}</td></tr>"
                    for _, r in dorm_df.iterrows()
                )
                content = f"""
                <table>
                  <tr><th>Кімната</th><th>Студент</th><th>Оплата</th><th>Примітки</th></tr>
                  {rows}
                </table>"""
                html = _build_pdf_html(content, "СПИСОК МЕШКАНЦІВ ГУРТОЖИТКУ")
                st.download_button("⬇️ Зберегти (.html)", html.encode('utf-8'),
                                   "dormitory_list.html", "text/html")

    # ── ВІДОМІСТЬ СТИПЕНДІАТІВ ────────────────────────────────────────────
    elif doc_type == "💰 Відомість стипендіатів":
        sch_df = pd.read_sql(
            "SELECT student_name, type, amount, status, date_assigned FROM scholarship "
            "WHERE status='Активна' ORDER BY type, student_name",
            conn
        )
        if sch_df.empty:
            st.warning("Немає активних стипендіатів.")
        else:
            total = sch_df['amount'].sum()
            st.metric("💰 Загальний фонд", f"{total:,} грн")
            st.dataframe(sch_df, use_container_width=True)
            if st.button("📥 Завантажити відомість (.html)", type="primary"):
                rows = "".join(
                    f"<tr><td>{i+1}</td><td>{r['student_name']}</td><td>{r['type']}</td>"
                    f"<td style='text-align:right'>{r['amount']} грн</td></tr>"
                    for i, (_, r) in enumerate(sch_df.iterrows())
                )
                content = f"""
                <p><b>Загальна сума:</b> {total:,} грн</p>
                <table>
                  <tr><th>№</th><th>ПІБ</th><th>Тип стипендії</th><th>Сума</th></tr>
                  {rows}
                  <tr><td colspan="3"><b>РАЗОМ</b></td><td style='text-align:right'><b>{total:,} грн</b></td></tr>
                </table>"""
                html = _build_pdf_html(content, "ВІДОМІСТЬ СТИПЕНДІАТІВ")
                st.download_button("⬇️ Зберегти (.html)", html.encode('utf-8'),
                                   "scholarship_list.html", "text/html")

    # ── СПИСКОВИЙ СКЛАД ГРУПИ ─────────────────────────────────────────────
    elif doc_type == "👥 Списковий склад групи":
        group = st.selectbox("Група", list(GROUPS_DATA.keys()))
        students_df = pd.read_sql(
            f"SELECT full_name FROM students WHERE group_name='{group}' ORDER BY full_name", conn
        )
        if students_df.empty:
            st.warning("Немає студентів у цій групі.")
        else:
            st.write(f"Студентів: **{len(students_df)}**")
            st.dataframe(students_df, use_container_width=True)
            if st.button("📥 Завантажити список (.html)", type="primary"):
                rows = "".join(
                    f"<tr><td>{i+1}</td><td>{r['full_name']}</td>"
                    f"<td></td><td></td></tr>"
                    for i, (_, r) in enumerate(students_df.iterrows())
                )
                content = f"""
                <p><b>Група:</b> {group} &nbsp;&nbsp; <b>Кількість студентів:</b> {len(students_df)}</p>
                <table>
                  <tr><th>№</th><th>ПІБ</th><th>Підпис</th><th>Примітки</th></tr>
                  {rows}
                </table>"""
                html = _build_pdf_html(content, f"СПИСКОВИЙ СКЛАД ГРУПИ {group}")
                st.download_button("⬇️ Зберегти (.html)", html.encode('utf-8'),
                                   f"group_list_{group}.html", "text/html")

    st.divider()
    st.info("💡 Завантажені файли у форматі HTML можна відкрити в браузері та роздрукувати "
            "(Ctrl+P) — браузер автоматично сформує правильний вигляд для друку.")
