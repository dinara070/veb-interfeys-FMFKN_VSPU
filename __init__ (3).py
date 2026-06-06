from .auth import login_register_page
from .main_panel import main_panel
from .students import students_groups_view
from .teachers import teachers_view
from .schedule import schedule_view
from .gradebook import gradebook_view
from .attendance import attendance_view
from .reports import reports_view
from .documents import documents_view
from .file_repository import file_repository_view
from .deanery_modules import deanery_modules_view
from .session_module import session_module_view
from .system_settings import system_settings_view

__all__ = [
    "login_register_page",
    "main_panel",
    "students_groups_view",
    "teachers_view",
    "schedule_view",
    "gradebook_view",
    "attendance_view",
    "reports_view",
    "documents_view",
    "file_repository_view",
    "deanery_modules_view",
    "session_module_view",
    "system_settings_view",
]
