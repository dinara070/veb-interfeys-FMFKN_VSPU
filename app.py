import streamlit as st

from db import init_db, migrate_db
from theme import init_theme, toggle_theme, apply_theme
from constants import DEAN_LEVEL

# ── Основні модулі ────────────────────────────────────────────────────────
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

# ── Нові модулі v2 ────────────────────────────────────────────────────────
from analytics import analytics_view
from calendar_events import calendar_view
from archive import archive_view
from pdf_generator import pdf_generator_view
from notifications import notifications_view

# ── КОНФІГУРАЦІЯ ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ФМФКН — Деканат",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# ── ІНІЦІАЛІЗАЦІЯ ─────────────────────────────────────────────────────────
init_theme()
apply_theme()
init_db()
migrate_db()   # Додає нові таблиці без втрати даних

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ── МАРШРУТИЗАЦІЯ ─────────────────────────────────────────────────────────
if not st.session_state['logged_in']:
    login_register_page()
else:
    current_role = st.session_state.get('role', '').lower()

    # ── SIDEBAR ──────────────────────────────────────────────────────────
    with st.sidebar:
        # Аватар + ім'я
        role_icons = {
            'admin': '🔑', 'dean': '🎓', 'teacher': '👨‍🏫',
            'student': '🎒', 'starosta': '📋'
        }
        icon = role_icons.get(current_role, '👤')
        st.markdown(f"""
        <div style="text-align:center; padding: 12px 0 8px;">
            <div style="font-size:2.5rem">{icon}</div>
            <div style="font-weight:700; font-size:1rem; margin-top:4px">
                {st.session_state.get('full_name', 'Користувач')}
            </div>
            <div style="font-size:0.8rem; color:#888; margin-top:2px">
                {current_role.upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Час входу
        if st.session_state.get('login_time'):
            st.caption(f"🕐 Сесія: {st.session_state['login_time']}")

        st.divider()

        # Кнопка теми
        theme_label = "🌙 Темна тема" if st.session_state.theme == 'light' else "☀️ Світла тема"
        if st.button(theme_label, use_container_width=True):
            toggle_theme()
            st.rerun()

        st.divider()

        # ── МЕНЮ НАВІГАЦІЇ ────────────────────────────────────────────────
        st.markdown("**📌 Навігація**")

        # Базові розділи — для всіх
        base_menu = {
            "🏠 Головна панель": main_panel,
            "📊 Аналітика": analytics_view,
            "📅 Календар подій": calendar_view,
            "👥 Студенти та Групи": students_groups_view,
            "👨‍🏫 Викладачі": teachers_view,
            "📅 Розклад занять": schedule_view,
            "💯 Електронний журнал": gradebook_view,
            "📝 Відвідуваність": attendance_view,
            "📊 Звіти та Пошук": reports_view,
            "📂 Документообіг": documents_view,
            "🗄️ Файловий репозиторій": file_repository_view,
        }

        # Розділи для деканату
        dean_menu = {}
        if current_role in DEAN_LEVEL:
            dean_menu = {
                "🏛️ Модулі Деканату": deanery_modules_view,
                "📑 Сесія та Рух": session_module_view,
                "🗂️ Архів студентів": archive_view,
                "🖨️ Генерація документів": pdf_generator_view,
                "📧 Email-розсилки": notifications_view,
            }

        # Системні розділи
        sys_menu = {}
        if current_role == 'admin':
            sys_menu = {"⚙️ Системні налаштування": system_settings_view}

        # Збираємо повне меню
        menu_options = {**base_menu, **dean_menu, **sys_menu}

        # Показуємо розділювачі між групами
        base_keys = list(base_menu.keys())
        dean_keys = list(dean_menu.keys())
        sys_keys = list(sys_menu.keys())

        if dean_keys:
            st.markdown('<small style="color:#888">── ДЕКАНАТ ──</small>', unsafe_allow_html=True)
        if sys_keys:
            st.markdown('<small style="color:#888">── СИСТЕМА ──</small>', unsafe_allow_html=True)

        selection = st.radio(
            "Навігація",
            list(menu_options.keys()),
            label_visibility="collapsed"
        )

        st.divider()

        # Вихід
        if st.button("🚪 Вийти", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── ОСНОВНИЙ КОНТЕНТ ──────────────────────────────────────────────────
    menu_options[selection]()
