import streamlit as st
from streamlit_cookies_controller import CookieController

# Імпортуємо з наших нових файлів
from config import DEAN_LEVEL
from database.db_core import init_db
from ui.theme import apply_theme, toggle_theme
from ui.auth import login_register_page
from ui.dashboard import main_panel
from ui.students import students_groups_view
from ui.teachers import teachers_view
from ui.schedule import schedule_view
from ui.grades import gradebook_view
from ui.attendance import attendance_view
from ui.documents import documents_view
from ui.files import file_repository_view
from ui.deanery import deanery_modules_view, session_module_view
from ui.settings import system_settings_view
from analytics.reports import reports_view

st.set_page_config(page_title="ФМФКН - Деканат", layout="wide", page_icon="🎓")

def main():
    # 1. Ініціалізація БД (з файлу database/db_core.py)
    init_db()
    
    # 2. Тема (функції з ui/theme.py)
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    apply_theme()

    # 3. Авторизація
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_register_page()
    else:
        # --- БОКОВА ПАНЕЛЬ ---
        st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")
        current_role = st.session_state.get('role', '').lower()

        if st.sidebar.button("Перемкнути тему 🌓"):
            toggle_theme()
            st.rerun()

        # --- НАВІГАЦІЯ ---
        menu_options = {
            "Головна панель": main_panel,
            "Студенти та Групи": students_groups_view,
            "Викладачі та Кафедри": teachers_view,
            "Розклад занять": schedule_view,
            "Електронний журнал": gradebook_view,
            "Журнал відвідуваності": attendance_view,
            "Звіти та Пошук": reports_view,
            "Документообіг": documents_view,
            "Файловий репозиторій": file_repository_view
        }

        if current_role in DEAN_LEVEL:
            menu_options["Модулі Деканату"] = deanery_modules_view
            menu_options["Сесія та Рух"] = session_module_view

        if current_role == 'admin':
            menu_options["Системні налаштування"] = system_settings_view

        selection = st.sidebar.radio("Навігація", list(menu_options.keys()))
        menu_options[selection]() # Виклик функції сторінки

        if st.sidebar.button("Вийти 🚪"):
            st.session_state['logged_in'] = False
            st.rerun()

if __name__ == '__main__':
    main()
