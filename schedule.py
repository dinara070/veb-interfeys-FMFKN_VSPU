import streamlit as st
import pandas as pd
import io

from db import create_connection
from groups_data import GROUPS_DATA
from constants import DEAN_LEVEL


def schedule_view():
    st.title("📅 Розклад")
    conn = create_connection()

    grp = st.selectbox("Група", list(GROUPS_DATA.keys()))
    df = pd.read_sql_query(
        f"SELECT day, time, subject, teacher FROM schedule WHERE group_name='{grp}'", conn
    )

    if not df.empty:
        st.subheader("📤 Експорт")
        c1, c2 = st.columns(2)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        c1.download_button("⬇️ Завантажити CSV", csv, f"schedule_{grp}.csv", "text/csv")

        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine='xlsxwriter')
        towrite.seek(0)
        c2.download_button("📊 Завантажити Excel", towrite, f"schedule_{grp}.xlsx",
                           "application/vnd.ms-excel")

        st.table(df)
    else:
        st.info("Наразі дані не завантажені.")

    if st.session_state.get('role') in DEAN_LEVEL:
        st.divider()

        st.subheader("📥 Імпорт файлу")
        uploaded_file = st.file_uploader("Оберіть файл для імпорту (CSV або Excel)", type=['csv', 'xlsx'])

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    new_data = pd.read_csv(uploaded_file)
                else:
                    new_data = pd.read_excel(uploaded_file)

                if st.button("🚀 Зберегти імпортовані дані"):
                    new_data['group_name'] = grp
                    new_data.to_sql('schedule', conn, if_exists='append', index=False)
                    st.success("Дані успішно додано!")
                    st.rerun()
            except Exception as e:
                st.error(f"Помилка формату: {e}")

        st.divider()

        with st.form("sch"):
            st.write("📝 Додати запис вручну")
            d = st.selectbox("День", ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"])
            t = st.selectbox("Час", [
                "08:30 - 09:50", "10:05 - 11:25", "11:40 - 13:00",
                "13:30 - 14:50", "15:00 - 16:20", "16:35 - 17:55"
            ])
            s = st.text_input("Предмет")
            tch = st.text_input("Викладач", value=st.session_state.get('full_name', ''))

            if st.form_submit_button("Додати"):
                if s:
                    conn.execute(
                        "INSERT INTO schedule (group_name, day, time, subject, teacher) VALUES (?,?,?,?,?)",
                        (grp, d, t, s, tch)
                    )
                    conn.commit()
                    st.rerun()
                else:
                    st.error("Введіть назву предмета!")
