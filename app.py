import streamlit as st
from streamlit_cookies_controller import CookieController

# Імпорт констант та налаштувань
from config import DEAN_LEVEL

# Імпорт логіки бази даних
from database.db_core import init_db

# Імпорт логіки UI (Темізація)
from ui.theme import apply_theme, toggle_theme

# Імпорт сторінок (Views)
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

# Імпорт модулів аналітики
from analytics.reports import reports_view

# Ініціалізація контролера кукі
controller = CookieController()

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="ФМФКН - Деканат", layout="wide", page_icon="🎓")

def main():
    # 1. Ініціалізація бази даних при старті додатку
    init_db()

    # 2. Ініціалізація стану сесії
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    # Застосування CSS стилів теми
    apply_theme()

    # 3. ЛОГІКА ВІДОБРАЖЕННЯ (Роутинг)
    if not st.session_state['logged_in']:
        # Якщо не авторизовані - показуємо сторінку входу
        login_register_page(controller) 
    else:
        # --- БОКОВА ПАНЕЛЬ (SIDEBAR) ---
        st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")

        current_role = st.session_state.get('role', '').lower()
        
        # Візуалізація ролі
        if current_role == 'student':
             st.sidebar.markdown("### 🛡️ СТУДЕНТ (READ ONLY)")
        elif current_role == 'tech_admin':
             st.sidebar.markdown("### ⚙️ ТЕХНІЧНИЙ АДМІНІСТРАТОР")
        elif current_role == 'teacher':
             st.sidebar.markdown("### 👨‍🏫 ВИКЛАДАЧ (ACADEMIC)")
        else:
             st.sidebar.caption(f"Роль: {current_role.upper()}")

        # Перемикач теми
        if st.sidebar.button("Перемкнути тему 🌓"):
            toggle_theme()
            st.rerun()

        st.sidebar.divider()

        # --- НАЛАШТУВАННЯ МЕНЮ НАВІГАЦІЇ ---
        menu_options = {
            "Головна панель": main_panel,
            "Студенти та Групи": students_groups_view,
            "Викладачі та Кафедри": teachers_view,
            "Розклад занять": schedule_view,
            "Електронний журнал": gradebook_view,
            "Журнал відвідуваності": attendance_view,
            "Звіти та Пошук": reports_view,       # Тягнеться з папки analytics/
            "Документообіг": documents_view,
            "Файловий репозиторій": file_repository_view
        }

        # Динамічне додавання пунктів меню залежно від прав
        if current_role in DEAN_LEVEL:
            menu_options["Модулі Деканату"] = deanery_modules_view
            menu_options["Сесія та Рух"] = session_module_view

        if current_role == 'admin':
            menu_options["Системні налаштування"] = system_settings_view

        # Вибір сторінки
        selection = st.sidebar.radio("Навігація", list(menu_options.keys()))

        # Запуск обраної функції-сторінки
        menu_options[selection]()

        st.sidebar.divider()

        # Кнопка виходу
        if st.sidebar.button("Вийти 🚪"):
            st.session_state['logged_in'] = False
            st.session_state.clear() # Очищення сесії для безпеки
            st.rerun()

if __name__ == '__main__':
    main()
