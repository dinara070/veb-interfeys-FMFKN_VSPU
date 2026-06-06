import streamlit as st
from config import TEACHERS_DATA


def teachers_view():
    st.title("👨‍🏫 Викладачі")

    # Ініціалізація даних викладачів у session_state
    if 'teachers_data' not in st.session_state:
        st.session_state.teachers_data = {k: list(v) for k, v in TEACHERS_DATA.items()}

    st.markdown("### 🛠️ Управління")
    tab_add, tab_import, tab_delete = st.tabs(["➕ Додати", "📥 Імпорт", "🗑️ Видалити"])

    with tab_add:
        with st.container(border=True):
            new_pib = st.text_input("ПІБ", placeholder="Прізвище Ім'я По батькові")
            target_dept = st.selectbox("Кафедра", list(st.session_state.teachers_data.keys()))
            if st.button("Додати", type="secondary"):
                if new_pib:
                    st.session_state.teachers_data[target_dept].insert(0, new_pib)
                    st.success(f"Викладача {new_pib} успішно додано!")
                    st.rerun()
                else:
                    st.error("Будь ласка, введіть ПІБ.")

    with tab_import:
        st.info("Виберіть файл форматів .csv або .xlsx для імпорту списку викладачів.")
        st.file_uploader("Завантажити файл", type=["csv", "xlsx"])

    with tab_delete:
        st.warning("Використовуйте іконку кошика 🗑️ біля прізвища викладача у списку нижче.")

    st.divider()

    for dept, teachers in st.session_state.teachers_data.items():
        with st.expander(f"📚 {dept}", expanded=True):
            if st.button(f"➕ Додати співробітника до: {dept[:20]}...", key=f"fast_add_{dept}"):
                st.info("Будь ласка, скористайтеся формою 'Управління' вгорі сторінки.")

            for i, t in enumerate(teachers):
                col_text, col_edit, col_del = st.columns([0.8, 0.05, 0.05])

                with col_text:
                    st.write(f"- {t}")
                with col_edit:
                    if st.button("✏️", key=f"edit_{dept}_{i}"):
                        st.toast(f"Режим редагування для: {t}")
                with col_del:
                    if st.button("🗑️", key=f"del_{dept}_{i}"):
                        st.session_state.teachers_data[dept].pop(i)
                        st.rerun()
