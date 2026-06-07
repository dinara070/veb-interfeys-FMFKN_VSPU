import streamlit as st
import pandas as pd

from db import create_connection, log_action, convert_df_to_csv
from constants import ROLES_LIST


def system_settings_view():
    st.title("Системні налаштування")

    if st.session_state['role'] != 'admin':
        st.error("Доступ заборонено! Тільки для адміністраторів.")
        return

    conn = create_connection()
    c = conn.cursor()

    t_roles, t_logs = st.tabs(["👥 Керування Ролями", "📜 Логи Дій"])

    with t_roles:
        st.header("Призначення прав доступу")
        users_df = pd.read_sql("SELECT username, full_name, role, group_link FROM users", conn)
        st.dataframe(users_df, use_container_width=True)

        st.divider()
        with st.form("change_role_form"):
            col_u, col_r = st.columns(2)
            u_select = col_u.selectbox("Оберіть користувача", users_df['username'].tolist())
            r_select = col_r.selectbox("Нова роль", ROLES_LIST)

            if st.form_submit_button("Змінити роль"):
                c.execute("UPDATE users SET role=? WHERE username=?", (r_select, u_select))
                conn.commit()
                log_action(st.session_state['full_name'], "Role Change",
                           f"Змінено роль {u_select} на {r_select}")
                st.success(f"Користувачу {u_select} призначено роль {r_select}")
                st.rerun()

    with t_logs:
        st.header("Журнал подій (Audit Log)")
        logs_df = pd.read_sql("SELECT * FROM system_logs ORDER BY id DESC", conn)

        col_fil1, col_fil2 = st.columns(2)
        filter_user = col_fil1.selectbox("Фільтр по користувачу",
                                         ["Всі"] + logs_df['user'].unique().tolist())
        filter_action = col_fil2.selectbox("Фільтр по дії",
                                           ["Всі"] + logs_df['action'].unique().tolist())

        if filter_user != "Всі":
            logs_df = logs_df[logs_df['user'] == filter_user]
        if filter_action != "Всі":
            logs_df = logs_df[logs_df['action'] == filter_action]

        st.dataframe(logs_df, use_container_width=True)
        st.download_button("⬇️ Завантажити лог (CSV)", convert_df_to_csv(logs_df),
                           "system_logs.csv", "text/csv")
