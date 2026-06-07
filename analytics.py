import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from db import create_connection
from groups_data import GROUPS_DATA
from constants import SUBJECTS_LIST, DEAN_LEVEL


def analytics_view():
    st.title("📊 Розширена Аналітика")
    conn = create_connection()

    # ── ФІЛЬТРИ ────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        all_groups = ["Всі групи"] + list(GROUPS_DATA.keys())
        sel_group = st.selectbox("Група", all_groups, key="an_grp")
    with col_f2:
        all_subjects = ["Всі предмети"] + SUBJECTS_LIST
        sel_subject = st.selectbox("Предмет", all_subjects, key="an_subj")
    with col_f3:
        period = st.selectbox("Період", ["Весь час", "Цей рік", "Цей семестр"])

    # WHERE-умови
    where_parts = []
    params = []
    if sel_group != "Всі групи":
        where_parts.append("group_name = ?")
        params.append(sel_group)
    if sel_subject != "Всі предмети":
        where_parts.append("subject = ?")
        params.append(sel_subject)
    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    grades_df = pd.read_sql(f"SELECT * FROM grades {where_sql}", conn, params=params)
    att_df = pd.read_sql(
        f"SELECT * FROM attendance {where_sql}", conn, params=params
    )

    # ── KPI ────────────────────────────────────────────────────────────────
    st.subheader("📌 Ключові показники")
    k1, k2, k3, k4, k5 = st.columns(5)

    total_st = pd.read_sql("SELECT count(*) FROM students", conn).iloc[0, 0]
    k1.metric("👥 Студентів", total_st)

    avg_g = round(grades_df['grade'].mean(), 2) if not grades_df.empty else 0
    k2.metric("📝 Середній бал", avg_g)

    excellent = 0
    if not grades_df.empty:
        avg_by_student = grades_df.groupby('student_name')['grade'].mean()
        excellent = int((avg_by_student >= 4.5).sum())
    k3.metric("🏆 Відмінників", excellent)

    absent_count = int((att_df['status'] == 'н').sum()) if not att_df.empty else 0
    k4.metric("❌ Пропусків", absent_count)

    docs_pending = pd.read_sql(
        "SELECT count(*) FROM documents WHERE status='Очікує'", conn
    ).iloc[0, 0]
    k5.metric("📋 Заяв очікує", docs_pending)

    st.divider()

    # ── РЯД 1: Успішність по групах + Розподіл оцінок ─────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Середній бал по групах")
        if not grades_df.empty:
            grp_avg = (
                grades_df.groupby('group_name')['grade']
                .mean().reset_index()
                .rename(columns={'grade': 'Середній бал', 'group_name': 'Група'})
                .sort_values('Середній бал', ascending=True)
            )
            fig = px.bar(
                grp_avg, x='Середній бал', y='Група', orientation='h',
                color='Середній бал',
                color_continuous_scale='RdYlGn',
                range_color=[1, 5],
                text='Середній бал',
                template='plotly_white'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10),
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Немає даних про оцінки.")

    with col2:
        st.subheader("🎯 Розподіл оцінок")
        if not grades_df.empty:
            grade_counts = grades_df['grade'].value_counts().reset_index()
            grade_counts.columns = ['Оцінка', 'Кількість']
            grade_counts = grade_counts.sort_values('Оцінка')
            colors_map = {1: '#ff4444', 2: '#ff8800', 3: '#ffcc00', 4: '#88cc44', 5: '#44bb44'}
            grade_counts['Колір'] = grade_counts['Оцінка'].map(colors_map)

            fig2 = px.pie(
                grade_counts, values='Кількість', names='Оцінка',
                color='Оцінка',
                color_discrete_map=colors_map,
                hole=0.4,
                template='plotly_white'
            )
            fig2.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Немає даних про оцінки.")

    # ── РЯД 2: Успішність по предметах + Відвідуваність ──────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📚 ТОП-10 предметів за успішністю")
        if not grades_df.empty:
            subj_avg = (
                grades_df.groupby('subject')['grade']
                .mean().reset_index()
                .rename(columns={'grade': 'Бал', 'subject': 'Предмет'})
                .sort_values('Бал', ascending=False)
                .head(10)
            )
            fig3 = px.bar(
                subj_avg, x='Предмет', y='Бал',
                color='Бал', color_continuous_scale='RdYlGn',
                range_color=[1, 5],
                template='plotly_white',
                text='Бал'
            )
            fig3.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig3.update_layout(
                height=380, margin=dict(l=10, r=10, t=10, b=10),
                xaxis_tickangle=-35, coloraxis_showscale=False
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Немає даних.")

    with col4:
        st.subheader("📅 Відвідуваність по групах")
        if not att_df.empty:
            att_grp = att_df.groupby('group_name').apply(
                lambda x: pd.Series({
                    'Присутні': (x['status'] == '').sum() + (x['status'] == 'присутній').sum(),
                    'Відсутні': (x['status'] == 'н').sum(),
                    'Н/п': (x['status'] == 'н/п').sum(),
                })
            ).reset_index()

            fig4 = px.bar(
                att_grp.melt(id_vars='group_name', var_name='Статус', value_name='Кількість'),
                x='group_name', y='Кількість', color='Статус',
                barmode='stack',
                color_discrete_map={'Присутні': '#44bb44', 'Відсутні': '#ff4444', 'Н/п': '#ff8800'},
                template='plotly_white',
                labels={'group_name': 'Група'}
            )
            fig4.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                               xaxis_tickangle=-35)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Немає даних про відвідуваність.")

    # ── РЯД 3: Рейтинг студентів ──────────────────────────────────────────
    st.subheader("🏅 Рейтинг студентів (ТОП-20)")
    if not grades_df.empty:
        rating = (
            grades_df.groupby(['student_name', 'group_name'])['grade']
            .agg(['mean', 'count'])
            .reset_index()
            .rename(columns={'mean': 'Середній бал', 'count': 'Оцінок', 'student_name': 'Студент', 'group_name': 'Група'})
            .sort_values('Середній бал', ascending=False)
            .head(20)
            .reset_index(drop=True)
        )
        rating.index += 1
        rating['Середній бал'] = rating['Середній бал'].round(2)

        # Медаль для топ-3
        def medal(i):
            return {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, str(i))

        rating.index = [medal(i) for i in rating.index]

        st.dataframe(
            rating.style.background_gradient(subset=['Середній бал'], cmap='RdYlGn', vmin=1, vmax=5),
            use_container_width=True
        )
    else:
        st.info("Немає даних для рейтингу.")

    # ── РЯД 4: Динаміка оцінок у часі ────────────────────────────────────
    st.subheader("📉 Динаміка успішності у часі")
    if not grades_df.empty and 'date' in grades_df.columns:
        try:
            grades_df['date'] = pd.to_datetime(grades_df['date'], errors='coerce')
            time_df = grades_df.dropna(subset=['date'])
            if not time_df.empty:
                time_avg = (
                    time_df.groupby(time_df['date'].dt.to_period('M'))['grade']
                    .mean().reset_index()
                )
                time_avg['date'] = time_avg['date'].astype(str)
                fig5 = px.line(
                    time_avg, x='date', y='grade',
                    markers=True,
                    labels={'date': 'Місяць', 'grade': 'Середній бал'},
                    template='plotly_white',
                    line_shape='spline'
                )
                fig5.update_traces(line_color='#667eea', marker_color='#764ba2', marker_size=8)
                fig5.add_hline(y=3.0, line_dash='dash', line_color='orange',
                               annotation_text='Мінімум (3.0)')
                fig5.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig5, use_container_width=True)
        except Exception:
            st.info("Недостатньо даних для динаміки.")
    else:
        st.info("Немає часових даних.")

    # ── ТАБЛИЦЯ ПРОБЛЕМНИХ СТУДЕНТІВ ──────────────────────────────────────
    st.subheader("⚠️ Студенти, що потребують уваги")
    if not grades_df.empty:
        problem = (
            grades_df.groupby(['student_name', 'group_name'])['grade']
            .mean().reset_index()
            .rename(columns={'grade': 'Середній бал', 'student_name': 'Студент', 'group_name': 'Група'})
        )
        problem = problem[problem['Середній бал'] < 3.0].sort_values('Середній бал')
        if not problem.empty:
            st.warning(f"Знайдено {len(problem)} студентів з середнім балом нижче 3.0")
            st.dataframe(
                problem.style.background_gradient(subset=['Середній бал'], cmap='Reds_r', vmin=0, vmax=3),
                use_container_width=True
            )
        else:
            st.success("✅ Немає студентів з критично низьким балом.")
    else:
        st.info("Немає даних.")
