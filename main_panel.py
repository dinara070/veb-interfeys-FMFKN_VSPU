import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

from db import create_connection
from constants import TEACHER_LEVEL


def main_panel():
    st.title("🏠 Головна панель")
    st.markdown(f"### Вітаємо, {st.session_state['full_name']}!")
    conn = create_connection()

    st.divider()
    st.subheader("📊 Аналітика та Статистика")
    kpi1, kpi2, kpi3 = st.columns(3)

    if st.session_state['role'] in ['student', 'starosta']:
        my_group = st.session_state['group']
        group_count = pd.read_sql_query(
            f"SELECT count(*) FROM students WHERE group_name='{my_group}'", conn
        ).iloc[0, 0]
        kpi1.metric("Моя група", f"{group_count} студ.")
    else:
        total_students = pd.read_sql_query("SELECT count(*) FROM students", conn).iloc[0, 0]
        kpi1.metric("Всього студентів", total_students)

    file_count = pd.read_sql_query("SELECT count(*) FROM file_storage", conn).iloc[0, 0]
    kpi2.metric("Завантажено матеріалів", file_count)

    if st.session_state['role'] in ['student', 'starosta']:
        avg_q = f"SELECT avg(grade) FROM grades WHERE student_name='{st.session_state['full_name']}'"
    else:
        avg_q = "SELECT avg(grade) FROM grades"
    avg_val = pd.read_sql_query(avg_q, conn).iloc[0, 0]
    avg_val = round(avg_val, 1) if avg_val else 0
    kpi3.metric("Середній бал", avg_val)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**📈 Успішність (Середній бал)**")
        if st.session_state['role'] in ['student', 'starosta']:
            query_chart = (
                f"SELECT subject, avg(grade) as avg_grade FROM grades "
                f"WHERE student_name='{st.session_state['full_name']}' GROUP BY subject"
            )
        else:
            query_chart = "SELECT subject, avg(grade) as avg_grade FROM grades GROUP BY subject"
        df_chart = pd.read_sql_query(query_chart, conn)
        if not df_chart.empty:
            st.bar_chart(df_chart.set_index('subject'))
        else:
            st.info("Наразі дані не завантажені.")

    with col_chart2:
        st.markdown("**📉 Відвідуваність**")
        q_att = (
            f"SELECT status FROM attendance WHERE student_name='{st.session_state['full_name']}'"
            if st.session_state['role'] in ['student', 'starosta']
            else "SELECT status FROM attendance"
        )
        df_att = pd.read_sql_query(q_att, conn)
        if not df_att.empty:
            absent_count = df_att[df_att['status'] != ''].shape[0]
            present_count = df_att[df_att['status'] == ''].shape[0]
            att_data = pd.DataFrame({
                'Статус': ['Присутній', 'Відсутній/Інше'],
                'Кількість': [present_count, absent_count]
            })
            base = alt.Chart(att_data).encode(theta=alt.Theta("Кількість", stack=True))
            pie = base.mark_arc(outerRadius=120).encode(
                color=alt.Color("Статус"),
                order=alt.Order("Кількість", sort="descending"),
                tooltip=["Статус", "Кількість"]
            )
            st.altair_chart(pie, use_container_width=True)
        else:
            st.info("Наразі дані не завантажені.")

    st.divider()
    st.subheader("📢 Оголошення та Новини")

    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📝 Додати нове оголошення"):
            with st.form("news_form"):
                n_title = st.text_input("Заголовок новини")
                n_msg = st.text_area("Текст оголошення")
                if st.form_submit_button("Опублікувати"):
                    if n_title and n_msg:
                        c = conn.cursor()
                        date_pub = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute(
                            "INSERT INTO news (title, message, author, date) VALUES (?,?,?,?)",
                            (n_title, n_msg, st.session_state['full_name'], date_pub)
                        )
                        conn.commit()
                        st.success("Новину опубліковано!")
                        st.rerun()

    news_df = pd.read_sql_query(
        "SELECT title, message, author, date FROM news ORDER BY id DESC", conn
    )
    if not news_df.empty:
        for i, row in news_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['title']}")
                st.write(row['message'])
                st.caption(f"🗓️ {row['date']} | ✍️ {row['author']}")
    else:
        st.info("Наразі немає актуальних оголошень.")
