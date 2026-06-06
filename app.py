import streamlit as st
from streamlit_cookies_controller import CookieController

# Імпорт конфігурації та модулів
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

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="ФМФКН - Деканат", layout="wide", page_icon="🎓")

def main():
    # 1. Ініціалізація бази даних
    init_db()
    
    # 2. Ініціалізація контролера та теми
    controller = CookieController()
    apply_theme()

    # 3. Стан сесії
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    # --- ЛОГІКА ВІДОБРАЖЕННЯ ---
    if not st.session_state['logged_in']:
        login_register_page() # Вона тепер використовує контролер всередині модуля
    else:
        # --- БОКОВА ПАНЕЛЬ ---
        st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")
        current_role = st.session_state.get('role', '').lower()

        # Відображення ролі
        st.sidebar.markdown(f"### 🏷️ {current_role.upper()}")

        if st.sidebar.button("Перемкнути тему 🌓"):
            toggle_theme()
            st.rerun()

        st.sidebar.divider()

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
        
        # Виклик функції обраної сторінки
        menu_options[selection]()

        st.sidebar.divider()
        if st.sidebar.button("Вийти 🚪"):
            st.session_state['logged_in'] = False
            st.session_state.clear()
            st.rerun()

if __name__ == '__main__':
    main()
