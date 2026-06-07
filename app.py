import streamlit as st

from db import init_db
from theme import init_theme, toggle_theme, apply_theme
from constants import DEAN_LEVEL
from auth import login_register_page
from main_panel import main_panel
from students import students_groups_view
from teachers import teachers_view
from schedule import schedule_view
from gradebook import gradebook_view
from attendance import attendance_view
from reports import reports_view
from documents import documents_view
from file_repository import file_repository_view
from deanery_modules import deanery_modules_view
from session_module import session_module_view
from system_settings import system_settings_view

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="ФМФКН - Деканат", layout="wide", page_icon="🎓")

# --- ІНІЦІАЛІЗАЦІЯ ---
init_theme()
apply_theme()
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- ЛОГІКА ВІДОБРАЖЕННЯ ---
if not st.session_state['logged_in']:
    login_register_page()
else:
    # --- БОКОВА ПАНЕЛЬ ---
    st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")

    current_role = st.session_state.get('role', '').lower()
    if current_role == 'student':
        st.sidebar.markdown("### 🛡️ СТУДЕНТ (READ ONLY)")
    elif current_role == 'tech_admin':
        st.sidebar.markdown("### ⚙️ ТЕХНІЧНИЙ АДМІНІСТРАТОР")
    elif current_role == 'teacher':
        st.sidebar.markdown("### 👨‍🏫 ВИКЛАДАЧ (ACADEMIC)")
    else:
        st.sidebar.caption(f"Роль: {current_role.upper()}")

    if st.sidebar.button("Перемкнути тему 🌓"):
        toggle_theme()
        st.rerun()

    st.sidebar.divider()

    # --- МЕНЮ НАВІГАЦІЇ ---
    menu_options = {
        "Головна панель": main_panel,
        "Студенти та Групи": students_groups_view,
        "Викладачі та Кафедри": teachers_view,
        "Розклад занять": schedule_view,
        "Електронний журнал": gradebook_view,
        "Журнал відвідуваності": attendance_view,
        "Звіти та Пошук": reports_view,
        "Документообіг": documents_view,
        "Файловий репозиторій": file_repository_view,
    }

    if current_role in DEAN_LEVEL:
        menu_options["Модулі Деканату"] = deanery_modules_view
        menu_options["Сесія та Рух"] = session_module_view

    if current_role == 'admin':
        menu_options["Системні налаштування"] = system_settings_view

    selection = st.sidebar.radio("Навігація", list(menu_options.keys()))
    menu_options[selection]()

    st.sidebar.divider()
    if st.sidebar.button("Вийти 🚪"):
        st.session_state['logged_in'] = False
        st.rerun()
