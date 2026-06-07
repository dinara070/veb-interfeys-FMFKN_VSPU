import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

from db import create_connection, log_action
from groups_data import GROUPS_DATA
from constants import DEAN_LEVEL

EVENT_TYPES = ["📚 Іспит", "📝 Залік", "📅 Дедлайн", "🎓 Подія", "⚠️ Засідання", "🏖️ Канікули", "📢 Оголошення"]
EVENT_COLORS = {
    "📚 Іспит": "#ff4444",
    "📝 Залік": "#ff8800",
    "📅 Дедлайн": "#cc44cc",
    "🎓 Подія": "#1f77b4",
    "⚠️ Засідання": "#ff6600",
    "🏖️ Канікули": "#44bb44",
    "📢 Оголошення": "#888888",
}


def calendar_view():
    st.title("📅 Календар Подій та Дедлайнів")
    conn = create_connection()
    c = conn.cursor()

    # ── ДОДАТИ ПОДІЮ (тільки dean/admin) ──────────────────────────────────
    if st.session_state.get('role') in DEAN_LEVEL:
        with st.expander("➕ Додати нову подію", expanded=False):
            with st.form("add_event_form"):
                col1, col2 = st.columns(2)
                title = col1.text_input("Назва події *", placeholder="Напр. Іспит з математики")
                event_type = col2.selectbox("Тип", EVENT_TYPES)
                col3, col4 = st.columns(2)
                event_date = col3.date_input("Дата", value=date.today())
                event_time = col4.text_input("Час (необов'язково)", placeholder="09:00")
                desc = st.text_area("Опис", placeholder="Додаткові деталі...")
                groups_sel = st.multiselect(
                    "Для груп (залиште порожнім = для всіх)",
                    list(GROUPS_DATA.keys())
                )
                if st.form_submit_button("📌 Зберегти подію", type="primary"):
                    if title:
                        group_str = ",".join(groups_sel) if groups_sel else "Всі"
                        c.execute(
                            "INSERT INTO calendar_events "
                            "(title, event_type, date, time, description, group_name, created_by, color) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (title, event_type, str(event_date), event_time, desc,
                             group_str, st.session_state['full_name'],
                             EVENT_COLORS.get(event_type, "#1f77b4"))
                        )
                        conn.commit()
                        log_action(st.session_state['full_name'], "Add Event", f"Подія: {title}")
                        st.success(f"✅ Подію '{title}' додано!")
                        st.rerun()
                    else:
                        st.error("Введіть назву події.")

    # ── ФІЛЬТРИ ────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_type = st.selectbox("Тип події", ["Всі"] + EVENT_TYPES)
    with col_f2:
        filter_period = st.selectbox("Показати", ["Найближчі 30 днів", "Цей місяць", "Все"])
    with col_f3:
        my_group = st.session_state.get('group', '')
        if st.session_state.get('role') in DEAN_LEVEL:
            filter_group = st.selectbox("Група", ["Всі"] + list(GROUPS_DATA.keys()))
        else:
            filter_group = my_group if my_group else "Всі"
            st.info(f"Показано події для: {filter_group or 'всіх'}")

    # ── ЗАВАНТАЖЕННЯ ПОДІЙ ─────────────────────────────────────────────────
    events_df = pd.read_sql(
        "SELECT * FROM calendar_events ORDER BY date ASC", conn
    )

    if events_df.empty:
        st.info("📭 Подій ще немає. Додайте першу подію!")
        return

    events_df['date'] = pd.to_datetime(events_df['date'], errors='coerce')
    today = pd.Timestamp(date.today())

    # Фільтр по часу
    if filter_period == "Найближчі 30 днів":
        events_df = events_df[
            (events_df['date'] >= today) &
            (events_df['date'] <= today + timedelta(days=30))
        ]
    elif filter_period == "Цей місяць":
        events_df = events_df[events_df['date'].dt.month == today.month]

    # Фільтр по типу
    if filter_type != "Всі":
        events_df = events_df[events_df['event_type'] == filter_type]

    # Фільтр по групі
    if filter_group != "Всі":
        events_df = events_df[
            events_df['group_name'].str.contains(filter_group, na=False) |
            (events_df['group_name'] == "Всі")
        ]

    if events_df.empty:
        st.info("Подій за обраними фільтрами не знайдено.")
        return

    # ── НАЙБЛИЖЧІ ПОДІЇ (банери) ───────────────────────────────────────────
    upcoming = events_df[events_df['date'] >= today].head(3)
    if not upcoming.empty:
        st.subheader("🔔 Найближчі події")
        cols = st.columns(min(len(upcoming), 3))
        for idx, (_, ev) in enumerate(upcoming.iterrows()):
            days_left = (ev['date'] - today).days
            color = ev.get('color', '#1f77b4')
            with cols[idx]:
                urgency = "🔴" if days_left <= 3 else ("🟡" if days_left <= 7 else "🟢")
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding: 12px;
                            border-radius: 8px; background: {'#fff5f5' if days_left<=3 else '#f8f9fa'};
                            margin-bottom: 8px;">
                    <b>{ev['event_type']}</b><br>
                    <b style="font-size:1.1rem">{ev['title']}</b><br>
                    <small>📅 {ev['date'].strftime('%d.%m.%Y')}{' о ' + ev['time'] if ev.get('time') else ''}</small><br>
                    <small>{urgency} {'Сьогодні!' if days_left==0 else f'Через {days_left} дн.'}</small>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── СПИСОК ПОДІЙ ПО ТИЖНЯХ ────────────────────────────────────────────
    st.subheader("📋 Усі події")
    events_df['week'] = events_df['date'].dt.isocalendar().week
    events_df['year'] = events_df['date'].dt.year

    for (year, week), week_events in events_df.groupby(['year', 'week']):
        first_day = week_events['date'].min()
        last_day = week_events['date'].max()
        label = f"Тиждень {int(week)}: {first_day.strftime('%d.%m')} — {last_day.strftime('%d.%m.%Y')}"

        with st.expander(f"📆 {label} ({len(week_events)} подій)", expanded=(year == today.year and week == today.isocalendar()[1])):
            for _, ev in week_events.iterrows():
                color = ev.get('color', '#1f77b4')
                is_past = ev['date'] < today
                opacity = "0.5" if is_past else "1"
                col_ev, col_del = st.columns([10, 1])
                with col_ev:
                    st.markdown(f"""
                    <div style="border-left:3px solid {color}; padding:8px 12px;
                                margin:4px 0; border-radius:4px; opacity:{opacity};">
                        <span style="color:{color}"><b>{ev['event_type']}</b></span> &nbsp;
                        <b>{ev['title']}</b>
                        <span style="float:right; color:#888; font-size:0.85rem">
                            {ev['date'].strftime('%d.%m.%Y')}{' ' + str(ev['time']) if ev.get('time') else ''}
                        </span><br>
                        <small style="color:#666">👥 {ev['group_name']}
                        {' | ' + str(ev['description']) if ev.get('description') else ''}</small>
                    </div>
                    """, unsafe_allow_html=True)
                if st.session_state.get('role') in DEAN_LEVEL:
                    with col_del:
                        if st.button("🗑️", key=f"del_ev_{ev['id']}"):
                            c.execute("DELETE FROM calendar_events WHERE id=?", (ev['id'],))
                            conn.commit()
                            st.rerun()

    # ── ЕКСПОРТ ────────────────────────────────────────────────────────────
    st.divider()
    export_df = events_df[['title', 'event_type', 'date', 'time', 'description', 'group_name']].copy()
    export_df['date'] = export_df['date'].dt.strftime('%d.%m.%Y')
    st.download_button(
        "⬇️ Завантажити календар (CSV)",
        export_df.to_csv(index=False).encode('utf-8-sig'),
        "calendar_events.csv", "text/csv"
    )
