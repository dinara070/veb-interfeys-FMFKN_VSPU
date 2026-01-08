import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_cookies_controller import CookieController
import pandas as pd
import hashlib
from datetime import datetime
import io
import altair as alt
import re

# Ініціалізація контролера кукі
controller = CookieController()

# --- КОНФІГУРАЦІЯ ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1PRSI150082txAU7fjscbdTvlUtSTj1t5nonYpdEPWQk/edit?usp=sharing"

st.set_page_config(page_title="ФМФКН - Деканат (Cloud)", layout="wide", page_icon="🎓")

# --- РОБОТА З GOOGLE SHEETS (ВИПРАВЛЕНО ДЛЯ ЗАПИСУ) ---

def get_connection():
    """Створює підключення. Налаштування мають бути в Secrets додатка."""
    return st.connection("gsheets", type=GSheetsConnection)

def read_sheet(sheet_name):
    """Безпечне читання аркуша"""
    try:
        conn = get_connection()
        # ВАЖЛИВО: ми не використовуємо SPREADSHEET_URL тут, 
        # бо URL має бути прописаний у secrets.toml
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how='all')
    except Exception:
        # Якщо аркуш порожній або помилка, повертаємо структуру, щоб не було помилок входу
        if sheet_name == "users":
            return pd.DataFrame(columns=["username", "password", "role", "full_name", "group_link"])
        return pd.DataFrame()

def save_sheet(sheet_name, df):
    """Повне оновлення аркуша (Потребує прав Service Account)"""
    try:
        conn = get_connection()
        # Очищуємо порожні рядки перед збереженням
        df = df.dropna(how='all')
        conn.update(worksheet=sheet_name, data=df)
        return True
    except Exception as e:
        # Не показуємо помилку користувачу відразу, а логуємо її для себе
        print(f"Error writing to {sheet_name}: {e}")
        return False

def append_row(sheet_name, new_row_dict):
    """Додавання рядка (Реєстрація)"""
    df = read_sheet(sheet_name)
    new_df = pd.concat([df, pd.DataFrame([new_row_dict])], ignore_index=True)
    if save_sheet(sheet_name, new_df):
        st.success(f"Запис в аркуш '{sheet_name}' успішний!")
    else:
        st.error(f"Помилка запису. Перевірте, чи додано Email сервісного акаунта як 'Редактора' в Google Таблиці!")
    
# --- БЕЗПЕКА ---

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def log_action(user_name, action, details):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_row("system_logs", {
        "user": user_name, 
        "action": action, 
        "details": details, 
        "timestamp": ts
    })

def perform_login(user_row):
    """Приймає рядок з DataFrame (Series)"""
    st.session_state['logged_in'] = True
    st.session_state['username'] = user_row['username']
    st.session_state['role'] = user_row['role']
    st.session_state['full_name'] = user_row['full_name']
    st.session_state['group'] = user_row['group_link']
    
    controller.set('remember_user', user_row['username']) 
    log_action(user_row['full_name'], "Login", "Вхід у хмарну систему")
    st.success(f"Вітаємо, {user_row['full_name']}!")
    st.rerun()
    
# --- ТЕМА ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

dark_css = "<style>.stApp { background-color: #0E1117; color: #FFFFFF; }</style>"
light_css = "<style>.stApp { background-color: #FFFFFF; color: #000000; }</style>"
st.markdown(dark_css if st.session_state.theme == 'dark' else light_css, unsafe_allow_html=True)

# --- КОНСТАНТИ ---
ROLES_LIST = ["dean", "admin"]
TEACHER_LEVEL = ['dean', 'admin']
DEAN_LEVEL = ['dean', 'admin']

# --- СПИСОК ПРЕДМЕТІВ ---
SUBJECTS_LIST = [
    "Філософія", "Історія і культура України", "Українська мова (за професійним спрямуванням)", "Педагогіка",
    "Іноземна мова для професійного спілкування", "Іноземна мова для академічного спілкування (магістри)", "Загальна психологія",
    "Вікова і педагогічна психологія", "Соціальна психологія", "Психологія (загальна)", "Психологія лідерства",
    "Історія педагогіки", "Методика виховної роботи", "Основи педагогічної майстерності", "Правознавство", 
    "Риторика",  "Література і кіно", "Права та свободи людини і громадянина", "Цивільний захист", "Безпека життєдіяльності та основи охорони праці",
    "Базова загальновійськова підготовка", "Тренінг розвитку стресостійкості", "Домедична допомога", "Фізична культура",
    "Польська мова: початковий курс", "Екологія", "Фінансова грамотність", "Числові системи", "Комп'ютерна статистика",
    "Математичний аналіз", "Лінійна алгебра", "Лінійна алгебра і аналітична геометрія", "Аналітична геометрія",
    "Алгебра і теорія чисел", "Елементарна математика", "Елементарна математика з точки зору вищої",
    "Диференціальні рівняння та рівняння математичної фізики", "Рівняння математичної фізики", 
    "Теорія ймовірностей та математична статистика", "Основи статистики і аналізу даних", "Прикладна статистика, педагогічні вимірювання та моніторинг якості освіти", 
    "Ймовірнісно-статистичні методи досліджень", "Математична логіка і теорія алгоритмів", "Дискретна математика",
    "Основи алгебри і дискретної математики", "Теорія алгоритмів", "Функціональний аналіз", "Комплексний аналіз",
    "Диференціальна геометрія і топологія", "Основи геометрії", "Конструктивна геометрія", "Додаткові розділи геометрії",
    "Комбінаторика і основи теорії ймовірностей", "Методи обчислень", "Методи оптимізації та дослідження операцій", 
    "Математичні методи у прийнятті рішень", "Системний аналіз та математичне моделювання", "Математичне моделювання природничих і соціально-економічних процесів", 
    "Математичні основи захисту інформації", "Інтегральні рівняння і варіаційне числення", "Асимптотичні методи математики", 
    "Основи аналізу Фур'є", "Основи теорії солітонів", "Аналіз випадкових процесів і ланцюги Маркова", 
    "Статистичні методи обробки експериментальних даних", "Історія математики", "Експериментальна фізика", 
    "Загальна фізика", "Механіка", "Молекулярна фізика і термодинаміка", "Електрика і магнетизм Оптика",
    "Атомна і ядерна фізика", "Практикум розв'язування задач з фізики", "Теоретична фізика",
    "Класична механіка", "Квантова механіка", "Статистична фізика і термодинаміка", "Електронна теорія речовини", 
    "Фізика та методика її навчання у ліцеях / академічних ліцеях", "Вибрані питання сучасної фізики, техніки, астрономії", 
    "Фізика живих систем", "Фізичні основи роботи біомедичної техніки", "Астрофізика", "Вибрані питання астрономії", 
    "Практикум з фізичного експерименту та астрономічних спостережень", "Сучасне природознавство і методика його навчання",
    "Інформатика (загальна)", "Інформатика та програмування", "Шкільний курс інформатики", "Інформаційні технології опрацювання даних"
    "Інформаційна культура", "Основи штучного інтелекту", "Машинне навчання в освіті", "Програмування", 
    "Сучасні технології програмування, машинне навчання та ШІ в освіті", "Алгоритми і структури даних",
    "Основи структурного та об'єктно-орієнтованого програмування", "Основи веб-програмування",
    "Побудова та аналіз алгоритмів у шкільній інформатиці", "Операційні системи та мережеві технології в шкільному курсі інформатики",
    "Архітектура та програмне забезпечення комп'ютерних систем", "Бази даних та інформаційні системи",
    "Системи керування базами даних", "Комп'ютерно орієнтовані технології навчання / в професійній діяльності", 
    "Цифрові технології обробки графічних зображень, анімації та відео", "Цифрові технології наукових досліджень", 
    "Системи комп'ютерної математики", "Комп'ютерне моделювання систем і процесів", "3D-моделювання", 
    "Основи кібербезпеки", "Технології захисту інформації", "Основи робототехніки та креативне програмування", 
    "Мобільні застосунки / технології у навчанні", "Дистанційний супровід шкільного курсу математики",
    "Спеціальна інформатика", "Програмні засоби математичного спрямування", "Основи теорії інтелектуальних систем",
    "Поглиблений курс шкільної інформатики", "Інклюзивний медіапростір: європейський досвід", 
    "Методика навчання інформатики", "Методика навчання математики", "Методика навчання фізики", 
    "Технології навчання фізики та астрономії", "Теорія і методика поглибленого навчання (алгебри, стереометрії)",
    "Наукові основи поглибленого навчання математики", "Теорія і практика математичних / інформатичних олімпіад",
    "Практикум розв'язування олімпіадних задач (алгебра, геометрія)", "Вибрані питання шкільного курсу фізики / математики", 
    "Методологія і методика наукових досліджень", "Педагогіка і психологія вищої школи", "Освітометрія",
    "Моделювання діяльності викладача математики ЗВО", "Моніторинг, діагностика та оцінювання навчання з математики", 
    "Інноваційні технології навчання математики", "Управління навчальними проектами / проєктною діяльністю", "Методика інклюзивного навчання інформатики",
    "Дослідницько-проєктувальна діяльність вчителя математики", "Інноваційний педагогічний досвід навчання математики",
    "Теорія і практика підготовки з фізики до ЗНО", "Практикум STEM-експерименту"
]

# --- ДАНІ (Студенти) ---
GROUPS_DATA = {
    "1СОМ": ["Алексєєнко Анна Олександрівна", "Гайдай Анатолій Олегович", "Журбелюк Павліна Павлівна", "Зарудняк Анастасія Сергіївна", "Книш Денис Олексійович", "Крапля Лілія Анатоліївна", "Логашкін Денис Владиславович", "Мазур Вероніка Сергіївна", "Мельник Богдан Олексійович", "Первий Андрій Миколайович", "Сулима Дарина Віталіївна", "Тимошенко Марія Миколаївна", "Шапельська Катерина Дмитрівна", "Шевчук Марія Олександрівна"],
    "1СОІ": ["Лисенко Тимофій Сергійович", "Лівий Павло Владиславович", "Муренко Степан Андрійович", "Поспелов Назар Андрійович", "Рибчук Андрій Олегович", "Томашевський Артем Васильович"],
    "1М": ["Басараба Олександр Ігорович", "Бондар Владислав Васильович", "Даньковський Нікіта Глібович", "Кокарєва Вікторія Олександрівна", "Сулима Маргаріта Андріївна", "Тишкіна Анастасія Павлівна"],
    "1СОФА": ["Генсіцька Аліна Миколаївна", "Курільченко Кіра Дмитрівна", "Мецгер Катерина Валеріївна", "Чернецька Наталія Сергіївна", "Шведун Валерій Володимирович"],
    "2СОМ": ["Адамлюк Владислав Романович", "Бичко Дар'я Юріївна", "Бугрова Юлія Вікторівна", "Бурейко Володимир Омелянович", "Гончарук Ангеліна Сергіївна", "Гріщенко Світлана Василівна", "Гунько Іван Романович", "Дорош Руслан Миколайович", "Журавель Альона Олександрович", "Зінченко Максим Олександрович", "Калінін Євген Олексійович", "Кисіль Яна Юріївна", "Киця Ярослав Володимирович", "Кравчук Юлія Юріївна", "Мартинюк Діана Сергіївна", "Назарук Діана Володимирівна", "Пасічник Софія Назарівна", "Пустовіт Анастасія Дмитрівна", "Пучкова Валерія Ігорівна", "Сичук Ангеліна Олександрівна", "Слободянюк Вікторія Вікторівна", "Стаськова Валентина Анатоліївна", "Харкевич Руслан Сергійович", "Черешня Станіслав Сергійович", "Чорна Єлизавета Миколаївна"],
    "2СОФА": ["Миколайчук Максим Олександрович", "Фурсік Марія Михайлівна"],
    "2СОІ": ["Адамов Владислав Виталійович", "Векшин Ігор Олександрович", "Діденко Артем Сергійович", "Кирилюк Ярослав Сергійович", "Кузовлєва Анастасія Сергіївна", "Новак Лілія Володимирівна", "Остапов Антон Юрійович", "Таранюк Степан Євгенійович", "Шило Гліб Олександрович", "Шпак Дар'я Володимирівна"],
    "2М": ["Блонський Владислав Ярославович", "Бондар Наталія Вікторівна", "Головата Валерія Олександрівна", "Граждан Тімур Костянтинович", "Гуцол Альона Василівна", "Левенець Владислава Дмитрівна", "Левченко Анна Миколаївна", "Миколаєнко Дмитро Олександрович", "Семенюк Ангеліна Дмитрівна", "Яцюк Вікторія Сергіївна"],
    "3СОМ": ["Винарчик Софія Степанівна", "Волинська Анна Сергіївна", "Кланцатий Костянтин Сергійович", "Крамар Анна Сергіївна", "Кузьменко Карина Леонідівна", "Лисаков Віталій Володимирович", "Лучко Анастасія Дмитрівна", "Мартиненко Владислав Ігорович", "Михайленко Вікторія Іванівна", "Нефедова Ксенія Євгеніїна", "Паплінська Ірина Петрівна", "Рудкевич Ольга Миколаївна", "Серветнік Лілія Ярославівна", "Усатюк Олександра Вадимівна", "Хованець Марʼяна Миколаївна", "Чернуха Софія Юріївна", "Шпортко Вікторія Михайлівна"],
    "3СОІ": ["Бабій Олександра Віталіївна", "Діхтяр Віталій Володимирович", "Довжок Віктор Петрович", "Казанок Єгор Михайлович", "Маковіцький Олексій Леонідович", "Письменний Сергій Васильович", "Репей Анна Сергіївна", "Станкевич Олександр Миколайович", "Стратійчук Іванна Олександрівна", "Шатковський Дмитро Петрович", "Шумило Дарина Василівна"],
    "3СОФА": ["Клапущак Богдан Віталійович", "Присяжнюк Іванна Олександрівна", "Стасюк Вадим Вольдемарович", "Теракт Дмитро Васильович", "Хіхло Ірина Валеріївна"],
    "3М": ["Бачок Микола Петрович", "Коберник Ірина Олександрівна", "Попіль Юліана Андріївна", "Семенець Вероніка Дмитрівна", "Цирульнікова Марина Віталіївна"],
    "4СОМ": ["Головата Марина Володимирівна", "Гріщенко Андрій Русланович", "Кліщ Юлія Сергіївна", "Мартинюк Анастасія Ігорівна", "Маховська Вікторія Юріївна", "Моцна Марія Анатоліївна", "Мруг Дарія Валентинівна", "Муляр Карина Сергіївна", "Неврюєва Дар'я Василівна", "Никитюк Юлія Ігорівна", "Павлова Вікторія Сергіївна", "Севастьянова Каріна Олегівна", "Стародуб Віталій", "Струбчевська Дар'я Вячеславівна", "Тімощенко Ірина Романівна", "Фаштинська Марія Василівна", "Фурман Наталія Вікторівна", "Ходик Аліна Радіонівна", "Швець Наталія Юріївна"],
    "4СОІ": ["Барановський Нікіта Ярославович", "Вишковська Вероніка Олександрівна", "Вогник Владислав Олександрович", "Зозуля Юлія Миколаївна", "Красілич Назарій Євгенович", "Мальований Віталій Вадимович", "Пелешок Анастасія Юріївна", "Савіна Карина Дмитрівна", "Сорока Олександр Миколайович", "Табашнюк Каріна Олександрівна", "Шикір Тарас Романович"],
    "4М": ["Карнаущук Анастасія Олегівна", "Коцюбан Діана Вікторівна", "Коцюбинська Анна Олександрівна", "Саїнчук Анастасія Павлівна", "Шельман Лілія Віталіївна", "Якимчук Аліна Юріївна"],
    "4СОФА": ["Дельнецький Ігор Андрійович", "Довгаль Марина Геннадіївна", "Зозуля Софія Андріївна", "Коваленко Анна Олександрівна", "Чаленко Ольга Володимирівна"],
    "1МСОІ": ["Афанасьєв Дмитро Андрійович", "Брижак Владислав Анатолійович", "Вавшко Віталій Сергійович", "Кізім Степан Вадимович", "Коваленко Марічка Сергіївна", "Корольов Максим Сергійович", "Мулярчук Сергій Павлович", "Никитюк Діана Валентинівна", "Раплєв Андрій Євгенович", "Шевчук Євген Ігорович"],
    "1ММ": ["Гетманчук Анна Валентинівна", "Кухта Іванка Іванівна", "Стесюк Анастасія Ігорівна", "Воробець Анастасія Віталіївна", "Куліш Олександра Романівна", "Логвіненко Ганна Олександрівна", "Онищук Олексій Олександрович", "Юрчук Дарина Олександрівна"],
    "1МСОМ": ["Комарова Каріна Вадимівна", "Злотковська Алла Віленівна", "Таранюк Надія Василівна", "Казмірчук Валентина Вікторівна", "Остапчук Діана Олегівна", "Пашківський Богдан Олексійович", "Михайльо Лідія Олександрівна", "Торкотюк Юрій Сергійович", "Климчук Анна Олександрівна", "Дячук Єгор Сергійович", "Іськов Ігор Валерійович", "Брицова Ілона Богданівна", "Романько Олена Олександрівна", "Біла Карина Русланівна", "Антошко Марина Олександрівна", "Бондаренко Єлена Олександрівна", "Гурман Катерина Ігорівна", "Донська Анастасія Ігорівна", "Поштарук Сніжана Сергіївна", "Байда Каріна Ігорівна", "Мамчур Мирослава Дмитрівна", "Салкевич Дарина Романівна", "Sемчук Олег Васильович"],
    "1МСОФА": ["Міщенко Владислав Сергійович", "Журжа Артем Арсенович", "Бережна Регіна Олександрівна", "Дмитренко Анастасія Олександрівна", "Дріма Віталій", "Олексійко Олександр Олександрович"],
    "2МСОМ": ["Ворожко Вікторія Олексіївна", "Гончар Сергій Віталійович", "Дзюняк Олександр Олексійович", "Зіняк Іванна Іванівна", "Іванова Анастасія Сергіївна", "Кеба Анастасія Олександрівна", "Козярчук Катерина Миколаївна", "Лещенко Тетяна Тимурівна", "Михайлюта Олена Василівна", "Руткевич Тетяна Іванівна", "Рябуха Вероніка Олександрівна", "Сидоренко Анна Олександрівна", "Тищенко Яна Михайлівна", "Шуриняк Олександр Ігорович"],
    "2МСОФА": ["Бусел Софія Юріївна", "Гулич Наталія Русланівна", "Кульпекін Ігор Миколайович", "Миронюк Марина Анатоліївна"],
    "2МСОІ": ["Коптєв Іван Валерійович", "Косенюк Марк Володимирович", "Таскаєв Дмитро Леонідович", "Шевчук Павло Вікторович"],
    "2ММ": ["Гриценко Володимир Борисович", "Дідусенко Анастасія Вікторівна", "Кізім Степан Вадимович", "Піменов Андрій Сергійович", "Чернієнко Артем Вікторович"]
}

# --- ДАНІ (Викладачі) ---
TEACHERS_DATA = {
    "Кафедра алгебри і методики навчання математики": [
        "Коношевський Олег Леонідович (Завідувач кафедри алгебри і методики навчання математики)", "Матяш Ольга Іванівна", "Михайленко Любов Федорівна", "Воєвода Аліна Леонідівна (Декан факультету математики, фізики і комп'ютерних наук)",
        "Вотякова Леся Андріївна", "Калашніков Ігор В’ячеславович", "Наконечна Людмила Йосипівна", "Панасенко Олексій Борисович (Заступник декана з навчальної роботи)",
        "Тютюнник Діана Олегівна", "Комарова Карина Вадимівна"
    ],
    "Кафедра математики та інформатики": [
        "Ковтонюк Мар'яна Михайлівна (Завідувач кафедри математики та інформатики)", "Бак Сергій Миколайович (Заступник декана з наукової роботи)", "Клочко Оксана Віталіївна",
        "Граняк Валерій Федорович", "Ковтонюк Галина Миколаївна", "Косовець Олена Павлівна (Заступник декана з виховної та соціальної роботи)", "Крупський Ярослав Володимирович",
        "Соя Олена Миколаївна", "Тютюн Любов Андріївна", "Леонова Іванна Миколаївна", "Поліщук Віталій Олегович", "Ярош Оксана Іванівна"
    ],
    "Кафедра фізики і методики навчання фізики, астрономії": [
        "Сільвейстр Анатолій Миколайович (Завідувач кафедри фізики і методики навчання фізики, астрономії)", "Заболотний Володимир Федорович", "Білюк Анатолій Іванович",
        "Думенко Вікторія Петрівна", "Моклюк Микола Олексійович", "Ксендзова Оксана Сергіївна", "Мамічева Інна Олексіївна",
        "Мороз Ярослав Олексійович", "Сіваєва Наталія Віталіївна", "Журжа Артем Арсенович"
    ]
}

# --- BACKEND ---

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_connection():
    return sqlite3.connect('university_v22.db', check_same_thread=False)

def log_action(user, action, details):
    conn = create_connection()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO system_logs (user, action, details, timestamp) VALUES (?,?,?,?)", (user, action, details, ts))
    conn.commit()

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

def create_connection():
    return sqlite3.connect('university_v22.db', check_same_thread=False)

def init_db():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, role TEXT, full_name TEXT, group_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, group_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS schedule(id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, day TEXT, time TEXT, subject TEXT, teacher TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, student_name TEXT, status TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS file_storage(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, file_content BLOB, upload_date TEXT, uploader TEXT, subject TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, type_of_work TEXT, grade INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, group_name TEXT, subject TEXT, date_column TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, message TEXT, author TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS dormitory(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, room_number TEXT, payment_status TEXT, comments TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scholarship(id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, type TEXT, amount INTEGER, status TEXT, date_assigned TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, details TEXT, timestamp TEXT)''')
    
    # --- ТАБЛИЦІ ДЛЯ АНКЕТИ ТА КОНТРАКТІВ ---
    c.execute('''CREATE TABLE IF NOT EXISTS student_education_info(
        student_name TEXT PRIMARY KEY,
        status TEXT, study_form TEXT, course INTEGER, is_contract TEXT,
        faculty TEXT, specialty TEXT, edu_program TEXT,
        referral_type TEXT, enterprise TEXT,
        enroll_protocol_num TEXT, enroll_order_num TEXT, enroll_condition TEXT,
        enroll_protocol_date TEXT, enroll_order_date TEXT, enroll_date TEXT,
        grad_order_num TEXT, grad_order_date TEXT, grad_date TEXT,
        student_id_card TEXT, gradebook_id TEXT, library_card TEXT,
        curator TEXT, last_modified TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS student_prev_education(
        student_name TEXT PRIMARY KEY,
        institution_name TEXT, institution_type TEXT,
        diploma_type TEXT, diploma_series TEXT, diploma_number TEXT,
        diploma_grades_summary TEXT, foreign_languages TEXT,
        last_modified TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS academic_certificates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT, cert_number TEXT, issue_date TEXT,
        source_institution TEXT, notes TEXT,
        added_by TEXT, added_date TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS individual_statements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT, subject TEXT, statement_type TEXT,
        reason TEXT, date_issued TEXT, status TEXT,
        created_by TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS student_contracts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        contract_number TEXT,
        date_signed TEXT,
        end_date TEXT,
        total_amount REAL,
        paid_amount REAL,
        payment_status TEXT,
        notes TEXT
    )''')

    # --- НОВА ТАБЛИЦЯ: ЕКЗАМЕНАЦІЙНІ ВІДОМОСТІ (СЕСІЯ) ---
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sheets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sheet_number TEXT,
        group_name TEXT,
        subject TEXT,
        control_type TEXT,
        exam_date TEXT,
        examiner TEXT,
        status TEXT
    )''')

    conn.commit()

    c.execute('SELECT count(*) FROM students')
    if c.fetchone()[0] == 0:
        c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)', ('admin', make_hashes('admin'), 'admin', 'Головний Адміністратор', ''))
        for group, names in GROUPS_DATA.items():
            for name in names:
                clean_name = name.lstrip("0123456789. ") 
                c.execute('INSERT INTO students (full_name, group_name) VALUES (?,?)', (clean_name, group))
        conn.commit()
    return conn

def log_action(user, action, details):
    conn = create_connection()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO system_logs (user, action, details, timestamp) VALUES (?,?,?,?)", (user, action, details, ts))
    conn.commit()

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

controller = CookieController()

def perform_login(user):
    """Обробка успішного входу в систему"""
    st.session_state['logged_in'] = True
    st.session_state['username'] = user[0]
    st.session_state['role'] = user[2]
    st.session_state['full_name'] = user[3]
    st.session_state['group'] = user[4]
    
    # Зберігаємо логін у кукі для автозаповнення при наступному візиті
    controller.set('user_login_hint', user[0]) 
    
    log_action(user[3], "Login", f"Вхід у систему")
    st.success(f"Вітаємо, {user[3]}!")
    st.rerun()

# --- СТОРІНКИ ---

def login_register_page():
    """Сторінка входу та реєстрації з використанням Google Sheets"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>🎓 Project Deanery .net</h2>", unsafe_allow_html=True)
        
        # Вибір режиму: Вхід або Реєстрація через вкладки
        mode = st.tabs(["🔐 Увійти", "📝 Реєстрація"])
        
        # Завантажуємо актуальний список користувачів з Google Sheets
        users_df = read_sheet("users")

        # --- ВКЛАДКА ВХОДУ ---
        with mode[0]:
            # Читаємо збережений логін з кукі браузера
            saved_username = controller.get('remember_user')
            
            username = st.text_input("Логін (Username):", value=saved_username if saved_username else "", key="login_user")
            password = st.text_input("Пароль:", type='password', key="login_pass")
            
            # Блок Капчі (залишаємо для безпеки)
            st.divider()
            captcha_val = "56388"
            st.markdown(f"**Код підтвердження:**")
            st.code(captcha_val, language=None)
            user_captcha = st.text_input("Введіть код, який ви бачите вище:", key="login_captcha")
            
            if st.button("Увійти в систему", use_container_width=True):
                if user_captcha != captcha_val:
                    st.error("❌ Невірний код підтвердження.")
                elif username and password:
                    if not users_df.empty:
                        hashed_input = make_hashes(password)
                        # Пошук користувача в DataFrame
                        user_match = users_df[(users_df['username'] == username) & (users_df['password'] == hashed_input)]
                        
                        if not user_match.empty:
                            # Отримуємо дані першого знайденого користувача
                            user_data = user_match.iloc[0]
                            # Викликаємо функцію авторизації (вже адаптовану під словник/Series)
                            perform_login(user_data)
                        else:
                            st.error("❌ Користувача не знайдено або пароль невірний.")
                    else:
                        st.warning("⚠️ База користувачів порожня. Будь ласка, зареєструйтесь.")
                else:
                    st.warning("⚠️ Заповніть усі поля для входу.")

        # --- ВКЛАДКА РЕЄСТРАЦІЇ ---
        with mode[1]:
            st.markdown("### Первинна реєстрація")
            st.info("Після реєстрації ваші дані будуть надійно збережені в хмарі Google Sheets.")
            
            new_user = st.text_input("Придумайте унікальний логін:", key="reg_user_new")
            new_pass = st.text_input("Придумайте надійний пароль:", type='password', key="reg_pass_new")
            full_name = st.text_input("Ваше повне ПІБ:", key="reg_full_name")
            role_choice = st.selectbox("Оберіть вашу посаду:", ROLES_LIST, key="reg_role_select")

            if st.button("Створити обліковий запис", use_container_width=True):
                if new_user and new_pass and full_name:
                    # Перевірка, чи не зайнятий логін
                    is_taken = False
                    if not users_df.empty:
                        is_taken = new_user in users_df['username'].values
                    
                    if is_taken:
                        st.error("⚠️ Цей логін вже зайнятий. Оберіть інший.")
                    else:
                        # Додаємо нового користувача в Google Sheets
                        new_user_data = {
                            "username": new_user,
                            "password": make_hashes(new_pass),
                            "role": role_choice,
                            "full_name": full_name,
                            "group_link": "Staff"
                        }
                        append_row("users", new_user_data)
                        
                        # Зберігаємо логін в кукі для зручності
                        controller.set('remember_user', new_user)
                        
                        st.success("🎉 Реєстрація успішна! Дані збережено в хмарі.")
                        st.info("Тепер перейдіть на вкладку **'🔐 Увійти'**.")
                        st.balloons()
                else:
                    st.warning("⚠️ Для реєстрації необхідно заповнити всі поля.")

def main_panel():
    st.title("🏠 Головна панель (Cloud)")
    st.markdown(f"### Вітаємо, {st.session_state['full_name']}!")
    
    # --- ЗАВАНТАЖЕННЯ ДАНИХ З GOOGLE SHEETS ---
    # Ми завантажуємо таблиці один раз для розрахунку аналітики
    students_df = read_sheet("students")
    grades_df = read_sheet("grades")
    attendance_df = read_sheet("attendance")
    news_df = read_sheet("news")
    # Для file_storage (якщо ви залишили аркуш для посилань)
    files_df = read_sheet("file_storage") 

    st.divider()
    st.subheader("📊 Аналітика та Статистика")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    # 1. Метрика студентів
    if st.session_state['role'] in ['student', 'starosta']:
        my_group = st.session_state['group']
        group_count = len(students_df[students_df['group_name'] == my_group]) if not students_df.empty else 0
        kpi1.metric("Моя група", f"{group_count} студ.")
    else:
        total_students = len(students_df) if not students_df.empty else 0
        kpi1.metric("Всього студентів", total_students)

    # 2. Метрика матеріалів
    file_count = len(files_df) if not files_df.empty else 0
    kpi2.metric("Завантажено матеріалів", file_count)

    # 3. Метрика середнього балу
    if not grades_df.empty:
        if st.session_state['role'] in ['student', 'starosta']:
            user_grades = grades_df[grades_df['student_name'] == st.session_state['full_name']]
            avg_val = user_grades['grade'].mean()
        else:
            avg_val = grades_df['grade'].mean()
        avg_val = round(avg_val, 1) if pd.notnull(avg_val) else 0
    else:
        avg_val = 0
    kpi3.metric("Середній бал", avg_val)

    # --- ГРАФІКИ ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("**📈 Успішність (Середній бал)**")
        if not grades_df.empty:
            if st.session_state['role'] in ['student', 'starosta']:
                chart_data = grades_df[grades_df['student_name'] == st.session_state['full_name']]
            else:
                chart_data = grades_df
            
            # Групування через Pandas (замість SQL GROUP BY)
            subj_avg = chart_data.groupby('subject')['grade'].mean().reset_index()
            st.bar_chart(subj_avg.set_index('subject'))
        else:
            st.info("Дані про оцінки відсутні.")

    with col_chart2:
        st.markdown("**📉 Відвідуваність**")
        if not attendance_df.empty:
            if st.session_state['role'] in ['student', 'starosta']:
                att_data = attendance_df[attendance_df['student_name'] == st.session_state['full_name']]
            else:
                att_data = attendance_df
            
            # Рахуємо статуси (н - відсутній, інші - присутній)
            absent_count = len(att_data[att_data['status'] == 'н'])
            present_count = len(att_data[att_data['status'] != 'н'])
            
            pie_df = pd.DataFrame({
                'Статус': ['Присутній', 'Відсутній'], 
                'Кількість': [present_count, absent_count]
            })
            
            base = alt.Chart(pie_df).encode(theta=alt.Theta("Кількість", stack=True))
            pie = base.mark_arc(outerRadius=100).encode(
                color=alt.Color("Статус"), 
                tooltip=["Статус", "Кількість"]
            )
            st.altair_chart(pie, use_container_width=True)
        else:
            st.info("Дані про відвідуваність відсутні.")

    st.divider()
    st.subheader("📢 Оголошення та Новини")
    
    # Форма додавання новин (тільки для викладачів/адмінів)
    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📝 Додати нове оголошення"):
            with st.form("news_form_cloud"):
                n_title = st.text_input("Заголовок новини")
                n_msg = st.text_area("Текст оголошення")
                if st.form_submit_button("Опублікувати"):
                    if n_title and n_msg:
                        new_news = {
                            "title": n_title,
                            "message": n_msg,
                            "author": st.session_state['full_name'],
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        append_row("news", new_news)
                        st.success("Новину збережено в Google Sheets!")
                        st.rerun()

    # Відображення новин
    if not news_df.empty:
        # Сортуємо: нові зверху
        for _, row in news_df.iloc[::-1].iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['title']}")
                st.write(row['message'])
                st.caption(f"🗓️ {row['date']} | ✍️ {row['author']}")
    else:
        st.info("Наразі немає актуальних оголошень.")

def students_groups_view():
    st.title("👥 Студенти та Групи")
    conn = create_connection()
    all_groups = ["Всі"] + list(GROUPS_DATA.keys())
    selected_group = st.selectbox("Фільтр по групі:", all_groups)
    query = "SELECT id, full_name as 'ПІБ', group_name as 'Група' FROM students"
    if selected_group != "Всі": query += f" WHERE group_name='{selected_group}'"
    df = pd.read_sql_query(query, conn)
    csv = convert_df_to_csv(df)
    st.download_button("⬇️ Експортувати (CSV)", csv, "students.csv", "text/csv")
    st.dataframe(df, use_container_width=True)
    
    if st.session_state['role'] in DEAN_LEVEL:
        st.divider()
        st.subheader("🛠️ Управління")
        t1, t2, t3 = st.tabs(["➕ Додати", "📥 Імпорт", "🗑️ Видалити"])
        with t1:
            with st.form("add_s"):
                nm = st.text_input("ПІБ")
                gr = st.selectbox("Група", list(GROUPS_DATA.keys()))
                if st.form_submit_button("Додати"):
                    c = conn.cursor()
                    c.execute('INSERT INTO students (full_name, group_name) VALUES (?,?)', (nm, gr))
                    conn.commit()
                    log_action(st.session_state['full_name'], "Add Student", f"Додано: {nm} в {gr}")
                    st.success("Додано!")
                    st.rerun()
        with t2:
            if st.session_state['role'] in ['admin', 'dean']:
                f = st.file_uploader("CSV (full_name, group_name)", type="csv")
                if f:
                    try:
                        df_new = pd.read_csv(f)
                        df_new[['full_name', 'group_name']].to_sql('students', conn, if_exists='append', index=False)
                        st.success("Імпортовано!")
                        st.rerun()
                    except Exception as e: st.error(f"Помилка: {e}")
        with t3:
            if st.session_state['role'] in ['admin', 'dean']:
                ids = pd.read_sql("SELECT id, full_name FROM students", conn)
                s_del = st.selectbox("Студент", ids.apply(lambda x: f"{x['id']}: {x['full_name']}", axis=1))
                if st.button("Видалити"):
                    sid = int(s_del.split(":")[0])
                    conn.execute("DELETE FROM students WHERE id=?", (sid,))
                    conn.commit()
                    st.success("Видалено")
                    st.rerun()

import streamlit as st

# --- ДАНІ (Викладачі) ---
if 'teachers_data' not in st.session_state:
    st.session_state.teachers_data = {
        "Кафедра алгебри і методики навчання математики": [
            "Коношевський Олег Леонідович (Завідувач кафедри алгебри і методики навчання математики)", 
            "Матяш Ольга Іванівна", "Михайленко Любов Федорівна", 
            "Воєвода Аліна Леонідівна (Декан факультету математики, фізики і комп'ютерних наук)",
            "Вотякова Леся Андріївна", "Калашніков Ігор В’ячеславович", "Наконечна Людмила Йосипівна", 
            "Панасенко Олексій Борисович (Заступник декана з навчальної роботи)",
            "Тютюнник Діана Олегівна", "Комарова Карина Вадимівна"
        ],
        "Кафедра математики та інформатики": [
            "Ковтонюк Мар'яна Михайлівна (Завідувач кафедри математики та інформатики)", 
            "Бак Сергій Миколайович (Заступник декана з наукової роботи)", "Клочко Оксана Віталіївна",
            "Граняк Валерій Федорович", "Ковтонюк Галина Миколаївна", 
            "Косовець Олена Павлівна (Заступник декана з виховної та соціальної роботи)", 
            "Крупський Ярослав Володимирович", "Соя Олена Миколаївна", "Тютюн Любов Андріївна", 
            "Леонова Іванна Миколаївна", "Поліщук Віталій Олегович", "Ярош Оксана Іванівна"
        ],
        "Кафедра фізики і методики навчання фізики, астрономії": [
            "Сільвейстр Анатолій Миколайович (Завідувач кафедри фізики і методики навчання фізики, астрономії)", 
            "Заболотний Володимир Федорович", "Білюк Анатолій Іванович",
            "Думенко Вікторія Петрівна", "Моклюк Микола Олексійович", "Ксендзова Оксана Сергіївна", 
            "Мамічева Інна Олексіївна", "Мороз Ярослав Олексійович", "Сіваєва Наталія Виталіївна", 
            "Журжа Артем Арсенович"
        ]
    }

def teachers_view():
    st.title("👨‍🏫 Викладачі")

    # --- 1. РОЗДІЛ "УПРАВЛІННЯ" ---
    st.markdown("### 🛠️ Управління")
    
    # Створення вкладок як на скриншоті
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

    # --- 2. СПИСОК КАФЕДР ТА ВИКЛАДАЧІВ (З функціями Admin) ---
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

import pandas as pd
import io
import streamlit as st

def schedule_view():
    st.title("📅 Розклад")
    conn = create_connection()
    
    grp = st.selectbox("Група", list(GROUPS_DATA.keys()))
    
    df = pd.read_sql_query(f"SELECT day, time, subject, teacher FROM schedule WHERE group_name='{grp}'", conn)
    
    if not df.empty:
        # --- СЕКЦІЯ ЕКСПОРТУ ---
        st.subheader("📤 Експорт")
        c1, c2 = st.columns(2)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        c1.download_button("⬇️ Завантажити CSV", csv, f"schedule_{grp}.csv", "text/csv")
        
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine='xlsxwriter')
        towrite.seek(0)
        c2.download_button("📊 Завантажити Excel", towrite, f"schedule_{grp}.xlsx", "application/vnd.ms-excel")
        
        st.table(df)
    else: 
        st.info("Наразі дані не завантажені.")
    
    # --- СЕКЦІЯ АДМІНІСТРАТОРА ---
    if st.session_state.get('role') in DEAN_LEVEL:
        st.divider()
        
        # --- ІМПОРТ ФАЙЛІВ ---
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

        # --- РУЧНЕ ДОДАВАННЯ ---
        with st.form("sch"):
            st.write("📝 Додати запис вручну")
            d = st.selectbox("День", ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"])
            t = st.selectbox("Час", ["08:30 - 09:50", "10:05 - 11:25", "11:40 - 13:00", "13:30 - 14:50", "15:00 - 16:20", "16:35 - 17:55"])
            s = st.text_input("Предмет")
            tch = st.text_input("Викладач", value=st.session_state.get('full_name', ''))
            
            if st.form_submit_button("Додати"):
                if s:
                    conn.execute("INSERT INTO schedule (group_name, day, time, subject, teacher) VALUES (?,?,?,?,?)", (grp, d, t, s, tch))
                    conn.commit()
                    st.rerun()
                else:
                    st.error("Введіть назву предмета!")

def documents_view():
    st.title("📂 Документообіг та Заяви")
    conn = create_connection()
    
    # Визначаємо список вкладок. Тепер їх лише дві основних
    tabs_list = ["📂 Реєстр / Мої заяви", "➕ Створити заяву"]
    
    # Якщо користувач — адміністратор, додаємо ТРЕТЮ вкладку (індекс 2)
    show_admin = st.session_state['role'] in DEAN_LEVEL
    if show_admin:
        tabs_list.append("⚙️ Обробка запитів")
    
    tabs = st.tabs(tabs_list)

    # --- Вкладка 1: Реєстр ---
    with tabs[0]:
        st.subheader("Історія документів")
        if st.session_state['role'] in ['student', 'starosta']:
            query = f"SELECT id, title as 'Тип документу', status as 'Статус', date as 'Дата подачі' FROM documents WHERE student_name='{st.session_state['full_name']}' ORDER BY id DESC"
        else:
            c1, c2 = st.columns([1, 3])
            filter_status = c1.selectbox("Фільтр за статусом", ["Всі", "Очікує", "Готово", "Відхилено"])
            base_q = "SELECT id, student_name as 'Студент', title as 'Тип документу', status as 'Статус', date as 'Дата' FROM documents"
            query = f"{base_q} WHERE status LIKE '{filter_status}%' ORDER BY id DESC" if filter_status != "Всі" else f"{base_q} ORDER BY id DESC"
        
        try:
            df_docs = pd.read_sql(query, conn)
            if not df_docs.empty:
                st.dataframe(df_docs, use_container_width=True)
            else:
                st.info("Список документів порожній")
        except Exception as e:
            st.error(f"Помилка завантаження даних: {e}")

    # --- Вкладка 2: Створити ---
    with tabs[1]:
        st.subheader("Подання нового запиту")
        with st.form("doc_create"):
            d_type = st.selectbox("Тип документу", [
                "Довідка про навчання (для ТЦК/Військкомату)",
                "Довідка про навчання (за місцем вимоги)",
                "Довідка про доходи",
                "Виписка з оцінками (Transcript)",
                "Заява на матеріальну допомогу",
                "Заява на поселення в гуртожиток",
                "Заява на індивідуальний графік"
            ])
            d_comment = st.text_input("Додаткові примітки (напр. 'В ТЦК м. Вінниця' або 'Терміново')")
            
            if st.form_submit_button("Надіслати запит"):
                full_title = f"{d_type}" + (f" ({d_comment})" if d_comment else "")
                conn.execute("INSERT INTO documents (title, student_name, status, date) VALUES (?,?,?,?)", 
                             (full_title, st.session_state['full_name'], "Очікує", str(datetime.now().date())))
                conn.commit()
                st.success("Запит успішно надіслано!")
                st.rerun()

    # --- Вкладка 3: Обробка ---
    if show_admin:
        with tabs[2]: # Змінено з tabs[3] на tabs[2]
            st.subheader("⚙️ Обробка запитів студентів")
            pending_docs = pd.read_sql("SELECT id, student_name, title, date FROM documents WHERE status='Очікує'", conn)
            
            if not pending_docs.empty:
                st.warning(f"Необроблених запитів: {len(pending_docs)}")
                req_id = st.selectbox("Оберіть запит", pending_docs['id'].tolist(), format_func=lambda x: f"ID {x}")
                sel_row = pending_docs[pending_docs['id']==req_id].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"**Студент:** {sel_row['student_name']} | **Запит:** {sel_row['title']}")
                    ac1, ac2 = st.columns(2)
                    new_status = ac1.selectbox("Рішення", ["Готово", "Відхилено", "В роботі"])
                    admin_comment = ac2.text_input("Коментар", placeholder="каб. 205")
                    
                    if st.button("✅ Застосувати рішення"):
                        final_status = new_status + (f" ({admin_comment})" if admin_comment else "")
                        conn.execute("UPDATE documents SET status=? WHERE id=?", (final_status, req_id))
                        conn.commit()
                        st.success("Статус оновлено")
                        st.rerun()
            else:
                st.success("🎉 Всі запити опрацьовано!")

def file_repository_view():
    st.title("🗄️ Файловий Репозиторій")
    conn = create_connection()
    c = conn.cursor()
    col_f1, col_f2 = st.columns([2,1])
    with col_f1: filter_subj = st.selectbox("📂 Фільтр по предмету", ["Всі"] + SUBJECTS_LIST)
    
    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📤 Завантажити"):
            with st.form("upload_form"):
                uploaded_file = st.file_uploader("Файл", accept_multiple_files=False)
                f_subject = st.selectbox("Предмет", SUBJECTS_LIST)
                f_desc = st.text_input("Опис")
                if st.form_submit_button("Зберегти"):
                    if uploaded_file and f_desc:
                        c.execute("INSERT INTO file_storage (filename, file_content, upload_date, uploader, subject, description) VALUES (?,?,?,?,?,?)",
                                  (uploaded_file.name, uploaded_file.read(), datetime.now().strftime("%Y-%m-%d %H:%M"), st.session_state['full_name'], f_subject, f_desc))
                        conn.commit()
                        st.success("Збережено!")
                        st.rerun()
    query = "SELECT id, filename, subject, description, upload_date, uploader FROM file_storage"
    if filter_subj != "Всі": query += f" WHERE subject='{filter_subj}'"
    df_files = pd.read_sql_query(query, conn)
    if not df_files.empty:
        for s in df_files['subject'].unique():
            st.subheader(f"📘 {s}")
            for i, row in df_files[df_files['subject'] == s].iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 4, 2, 1])
                    c1.write(f"📄 **{row['filename']}**")
                    c2.write(f"📝 {row['description']}")
                    c3.caption(f"{row['uploader']}")
                    data = c.execute("SELECT file_content FROM file_storage WHERE id=?", (row['id'],)).fetchone()[0]
                    c3.download_button("⬇️", data, row['filename'], key=f"d{row['id']}")
                    if st.session_state['role'] == 'admin':
                        if c4.button("🗑️", key=f"del_{row['id']}"):
                            c.execute("DELETE FROM file_storage WHERE id=?", (row['id'],))
                            conn.commit()
                            st.rerun()
    else: st.info("Наразі дані не завантажені.")

import pandas as pd
import io
import streamlit as st

def gradebook_view():
    st.title("💯 Електронний журнал (Google Sheets)")
    
    # Завантажуємо дані
    grades_df = read_sheet("grades")
    students_df = read_sheet("students")
    
    if students_df.empty:
        st.error("База студентів порожня. Додайте студентів у відповідній вкладці.")
        return

    # --- ЛОГІКА ДЛЯ СТУДЕНТА / СТАРОСТИ (Тільки перегляд) ---
    if st.session_state.get('role') in ['student', 'starosta']:
        st.subheader(f"Оцінки студента: {st.session_state['full_name']}")
        if not grades_df.empty:
            user_grades = grades_df[grades_df['student_name'] == st.session_state['full_name']]
            if not user_grades.empty:
                st.dataframe(user_grades[['subject', 'type_of_work', 'grade', 'date']], use_container_width=True)
            else:
                st.info("У вас поки немає виставлених оцінок.")
        else:
            st.info("Журнал порожній.")
            
    # --- ЛОГІКА ДЛЯ АДМІНІСТРАТОРА / ВИКЛАДАЧА (Редагування) ---
    else:
        t_journal, t_ops = st.tabs(["📊 Редактор журналу", "📥/📤 Імпорт та Експорт"])
        
        # Загальні фільтри для обох вкладок
        c1, c2, c3 = st.columns(3)
        all_groups = sorted(students_df['group_name'].unique().tolist())
        grp = c1.selectbox("Група", all_groups)
        st_in_grp = students_df[students_df['group_name'] == grp]['full_name'].tolist()
        selected_student = c2.selectbox("Студент", ["Всі студенти"] + st_in_grp)
        subj = c3.selectbox("Предмет", SUBJECTS_LIST)

        with t_journal:
            # Блок додавання нової колонки (з першого варіанту)
            with st.expander("➕ Додати нову колонку (Модуль, Лабораторна тощо)"):
                with st.form("new_col_form"):
                    work_name = st.text_input("Назва роботи")
                    work_date = st.date_input("Дата")
                    if st.form_submit_button("Створити колонку для групи"):
                        if work_name:
                            new_rows = []
                            for s in st_in_grp:
                                new_rows.append({
                                    "student_name": s, "group_name": grp, "subject": subj,
                                    "type_of_work": work_name, "grade": 0, "date": str(work_date)
                                })
                            updated_grades = pd.concat([grades_df, pd.DataFrame(new_rows)], ignore_index=True)
                            save_sheet("grades", updated_grades)
                            st.success(f"Колонку '{work_name}' успішно додано!")
                            st.rerun()

            # Основний редактор (з вашого другого варіанту)
            mask = (grades_df['group_name'] == grp) & (grades_df['subject'] == subj) if not grades_df.empty else pd.Series([False]*len(grades_df))
            if selected_student != "Всі студенти":
                mask = mask & (grades_df['student_name'] == selected_student)
            
            raw_filtered = grades_df[mask] if not grades_df.empty else pd.DataFrame()

            if not raw_filtered.empty:
                # Трансформуємо в матрицю для data_editor
                matrix = raw_filtered.pivot(index='student_name', columns='type_of_work', values='grade').fillna(0)
                st.write(f"**Редагування оцінок: {grp} — {subj}**")
                edited_matrix = st.data_editor(matrix, use_container_width=True)
                
                if st.button("💾 Зберегти всі зміни в хмару"):
                    # Логіка розумного оновлення
                    other_grades = grades_df[~mask] if not grades_df.empty else pd.DataFrame()
                    
                    new_entries = []
                    for s_name, row in edited_matrix.iterrows():
                        for work_type, val in row.items():
                            new_entries.append({
                                "student_name": s_name, "group_name": grp, "subject": subj,
                                "type_of_work": work_type, "grade": val, "date": str(datetime.now().date())
                            })
                    
                    final_df = pd.concat([other_grades, pd.DataFrame(new_entries)], ignore_index=True)
                    save_sheet("grades", final_df)
                    st.success("Дані успішно синхронізовано!")
                    st.rerun()
            else:
                st.info("Даних для відображення немає. Додайте колонку вище.")

        with t_ops:
            # Функції експорту та імпорту (з першого варіанту)
            st.subheader("Вивантаження та завантаження даних")
            if not raw_filtered.empty:
                c_ex1, c_ex2 = st.columns(2)
                csv = raw_filtered.to_csv(index=False).encode('utf-8-sig')
                c_ex1.download_button("⬇️ Завантажити CSV", csv, f"grades_{grp}_{subj}.csv", "text/csv")
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    raw_filtered.to_excel(writer, index=False)
                c_ex2.download_button("📊 Завантажити Excel", buffer.getvalue(), f"grades_{grp}_{subj}.xlsx")
            
            st.divider()
            up_file = st.file_uploader("Масовий імпорт оцінок (CSV/XLSX)", type=["csv", "xlsx"])
            if up_file and st.button("🚀 Запустити імпорт"):
                try:
                    df_new = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    combined = pd.concat([grades_df, df_new], ignore_index=True)
                    save_sheet("grades", combined)
                    st.success("Дані імпортовано!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Помилка: {e}")
                    
import io
import pandas as pd
import streamlit as st

def attendance_view():
    st.title("📝 Журнал Відвідуваності")
    conn = create_connection()
    
    # --- ЛОГІКА ДЛЯ СТУДЕНТА ---
    if st.session_state['role'] == 'student':
        df_att = pd.read_sql(
            f"SELECT subject as 'Предмет', date_column as 'Дата', status as 'Статус' "
            f"FROM attendance WHERE student_name='{st.session_state['full_name']}'", 
            conn
        )
        st.dataframe(df_att, use_container_width=True)
        
    # --- ЛОГІКА ДЛЯ АДМІНІСТРАТОРА / ВИКЛАДАЧА ---
    else:
        # Вибір контексту: Група та Предмет
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Група", list(GROUPS_DATA.keys()), key="att_grp")
        subj = c2.selectbox("Предмет", SUBJECTS_LIST, key="att_sbj")
        
        # --- БЛОК ДОДАВАННЯ ТА ІМПОРТУ ---
        col_add, col_imp = st.columns(2)
        
        with col_add:
            with st.expander("➕ Додати дату вручну"):
                with st.form("new_att_col"):
                    col_name = st.text_input("Назва дати (напр. 25.12)")
                    
                    stds_in_grp = pd.read_sql(
                        f"SELECT full_name FROM students WHERE group_name='{grp}'", 
                        conn
                    )['full_name'].tolist()
                    
                    student_selection = st.selectbox(
                        "Для кого додати:",
                        ["Усі студенти"] + stds_in_grp
                    )
                    
                    default_status = st.selectbox(
                        "Статус за замовчуванням:",
                        ["", "присутній", "н", "н/п", "з"]
                    )
                    
                    if st.form_submit_button("Створити"):
                        if col_name:
                            targets = stds_in_grp if student_selection == "Усі студенти" else [student_selection]
                            
                            for s in targets:
                                exists = conn.execute(
                                    "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?", 
                                    (s, subj, col_name)
                                ).fetchone()
                                
                                if not exists:
                                    conn.execute(
                                        "INSERT INTO attendance (student_name, group_name, subject, date_column, status) VALUES (?,?,?,?,?)", 
                                        (s, grp, subj, col_name, default_status)
                                    )
                            conn.commit()
                            st.success(f"Записи для '{col_name}' успішно створено!")
                            st.rerun()
                        else:
                            st.error("Будь ласка, введіть назву дати!")

        with col_imp:
            with st.expander("📥 Імпорт з Excel"):
                uploaded_file = st.file_uploader("Завантажте файл .xlsx", type="xlsx")
                if uploaded_file:
                    imp_df = pd.read_excel(uploaded_file, index_col=0)
                    if st.button("Підтвердити імпорт"):
                        for s_name, row in imp_df.iterrows():
                            for d_col, val in row.items():
                                val = str(val) if pd.notna(val) else ""
                                res = conn.execute(
                                    "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?", 
                                    (s_name, subj, d_col)
                                ).fetchone()
                                
                                if res:
                                    conn.execute("UPDATE attendance SET status=? WHERE id=?", (val, res[0]))
                                else:
                                    conn.execute(
                                        "INSERT INTO attendance (student_name, group_name, subject, date_column, status) VALUES (?,?,?,?,?)", 
                                        (s_name, grp, subj, d_col, val)
                                    )
                        conn.commit()
                        st.success("Дані з файлу успішно імпортовано!")
                        st.rerun()

        # --- ОТРИМАННЯ ТА ОБРОБКА ДАНИХ ДЛЯ ТАБЛИЦІ ---
        raw = pd.read_sql(
            f"SELECT student_name, date_column, status FROM attendance WHERE group_name='{grp}' AND subject='{subj}'", 
            conn
        )
        
        if not raw.empty:
            matrix = raw.pivot_table(index='student_name', columns='date_column', values='status', aggfunc='first').fillna("")
            
            st.divider()
            
            f_col1, f_col2 = st.columns([2,1])
            
            with f_col1:
                missed_counts = (matrix == "н").sum(axis=1)
                max_misses = int(missed_counts.max()) if not missed_counts.empty else 0
                n_filter = st.slider("🔍 Фільтр прогульників: Студенти з 'н' >= N:", 0, max_misses, 0)
            
            with f_col2:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    matrix.to_excel(writer, sheet_name='Відвідуваність')
                
                st.write("📫 Звітність")
                st.download_button(
                    label="📥 Завантажити Excel",
                    data=buffer.getvalue(),
                    file_name=f"Attendance_{grp}_{subj}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            filtered_matrix = matrix[missed_counts >= n_filter]

            column_config = {
                col: st.column_config.SelectboxColumn(
                    col,
                    options=["", "присутній", "н", "н/п", "з"],
                    width="small"
                ) for col in filtered_matrix.columns
            }

            st.write(f"### 📋 Журнал: {grp} — {subj}")
            st.info("💡 Ви можете змінювати статуси прямо в таблиці та натиснути кнопку 'Зберегти' внизу.")
            
            edited = st.data_editor(
                filtered_matrix, 
                column_config=column_config,
                use_container_width=True
            )
            
            if st.button("💾 Зберегти зміни у журналі"):
                for s_name, row in edited.iterrows():
                    for d_col, val in row.items():
                        db_res = conn.execute(
                            "SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?", 
                            (s_name, subj, d_col)
                        ).fetchone()
                        
                        if db_res: 
                            conn.execute("UPDATE attendance SET status=? WHERE id=?", (val, db_res[0]))
                            
                conn.commit()
                st.success("Усі зміни успішно записані в базу даних!")
                st.rerun()
        else:
            st.info("У журналі поки немає даних для обраної групи та предмета. Додайте дату вручну або завантажте Excel-файл.")

import pandas as pd
import io
import streamlit as st
from datetime import datetime

def reports_view():
    st.title("📊 Звіти та Пошук")
    conn = create_connection()
    c = conn.cursor()
    t1, t2, t3 = st.tabs(["📋 Відомість (Група/Предмет)", "🎓 Картка Студента", "📈 Зведена відомість"])
    
    with t1:
        st.subheader("Формування відомості")
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Група", list(GROUPS_DATA.keys()), key="rep_grp")
        subj = c2.selectbox("Предмет", SUBJECTS_LIST, key="rep_subj")
        
        raw = pd.read_sql(f"SELECT student_name, type_of_work, grade FROM grades WHERE group_name='{grp}' AND subject='{subj}'", conn)
        
        if not raw.empty:
            matrix = raw.pivot_table(index='student_name', columns='type_of_work', values='grade', aggfunc='first').fillna(0)
            st.dataframe(matrix, use_container_width=True)
            
            # --- БЛОК ЕКСПОРТУ ---
            st.markdown("#### Експорт відомості")
            ex_c1, ex_c2, ex_c3 = st.columns(3)
            
            ex_c1.download_button("⬇️ CSV", matrix.to_csv().encode('utf-8-sig'), f"vidomist_{grp}_{subj}.csv", "text/csv")
            
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    matrix.to_excel(writer, sheet_name='Відомість')
                ex_c2.download_button("📊 Excel", buf.getvalue(), f"vidomist_{grp}_{subj}.xlsx", "application/vnd.ms-excel")
            except:
                ex_c2.info("Excel двигун не знайдено")
                
            # JSON
            ex_c3.download_button("📜 JSON", matrix.to_json(force_ascii=False), f"vidomist_{grp}_{subj}.json", "application/json")
        else:
            st.warning("Наразі дані не завантажені.")

    with t2:
        st.subheader("Електронна Анкета Студента")
        all_students = pd.read_sql("SELECT full_name FROM students", conn)
        if not all_students.empty:
            selected_student = st.selectbox("Оберіть студента", all_students['full_name'].tolist())
            
            if st.button("📤 Експортувати всі дані студента (JSON)"):
                student_full_data = {
                    "main": pd.read_sql(f"SELECT * FROM students WHERE full_name='{selected_student}'", conn).to_dict('records'),
                    "edu": pd.read_sql(f"SELECT * FROM student_education_info WHERE student_name='{selected_student}'", conn).to_dict('records'),
                    "prev_edu": pd.read_sql(f"SELECT * FROM student_prev_education WHERE student_name='{selected_student}'", conn).to_dict('records'),
                    "grades": pd.read_sql(f"SELECT * FROM grades WHERE student_name='{selected_student}'", conn).to_dict('records')
                }
                st.download_button("Завантажити JSON анкету", str(student_full_data), f"anketa_{selected_student}.json")

            tab_main, tab_edu, tab_prev_edu, tab_grades = st.tabs(["Загальна", "Навчання (Поточне)", "Освіта (До вступу)", "Успішність"])
            

            with tab_grades:
                grades = pd.read_sql(f"SELECT subject, type_of_work, grade, date FROM grades WHERE student_name='{selected_student}'", conn)
                if not grades.empty:
                    st.dataframe(grades, use_container_width=True)
                    st.metric("Середній бал", f"{grades['grade'].mean():.2f}")
                else: st.info("Оцінок немає.")
        else: st.error("Наразі дані не завантажені.")

    with t3:
        st.subheader("Генератор Зведеної Відомості")
        
        try:
            db_groups = pd.read_sql("SELECT DISTINCT group_name FROM students", conn)['group_name'].tolist()
        except:
            db_groups = list(GROUPS_DATA.keys())
            
        grp_sum = st.selectbox("Оберіть групу", db_groups, key="rep_sum_grp")
        
        # --- БЛОК ІМПОРТУ ---
        with st.expander("📥 Імпорт даних у зведену відомість"):
            up_file = st.file_uploader("Завантажте CSV або Excel", type=['csv', 'xlsx'], key="import_sum")
            if up_file and st.button("🚀 Виконати імпорт"):
                try:
                    df_imp = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    df_imp.to_sql('grades', conn, if_exists='append', index=False)
                    st.success("Дані успішно імпортовані!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Помилка імпорту: {e}")

        try:
            available_subjects_query = f"SELECT DISTINCT subject FROM grades WHERE group_name='{grp_sum}'"
            available_subjects = pd.read_sql(available_subjects_query, conn)['subject'].tolist()
        except:
            available_subjects = []

        if not available_subjects:
            available_subjects = SUBJECTS_LIST
            
        selected_subjects = st.multiselect("Оберіть предмети для відомості", options=available_subjects, default=available_subjects[:5] if len(available_subjects) > 5 else available_subjects)
        
        if st.button("🔄 Згенерувати таблицю"):
            if selected_subjects:
                try:
                    # Використовуємо параметризований запит для безпеки
                    subjects_placeholder = ",".join(["?"] * len(selected_subjects))
                    query = f"""
                        SELECT student_name, subject, AVG(grade) as final_grade 
                        FROM grades 
                        WHERE group_name = ? AND subject IN ({subjects_placeholder}) 
                        GROUP BY student_name, subject
                    """
                    params = [grp_sum] + selected_subjects
                    data = pd.read_sql(query, conn, params=params)
                    
                    if not data.empty:
                        summary_matrix = data.pivot_table(index='student_name', columns='subject', values='final_grade').fillna(0).round(0).astype(int)
                        
                        all_students_df = pd.read_sql("SELECT full_name FROM students WHERE group_name=?", conn, params=[grp_sum])
                        summary_matrix = all_students_df.merge(summary_matrix, left_on='full_name', right_index=True, how='left').fillna(0)
                        summary_matrix.set_index('full_name', inplace=True)
                        
                        st.success(f"Згенеровано відомість для групи {grp_sum}")
                        st.dataframe(summary_matrix, use_container_width=True)
                        
                        c_sum1, c_sum2 = st.columns(2)
                        csv_out = summary_matrix.to_csv().encode('utf-8-sig')
                        c_sum1.download_button("⬇️ Експорт CSV", csv_out, f"zvedena_{grp_sum}.csv")
                        
                        try:
                            buf_sum = io.BytesIO()
                            with pd.ExcelWriter(buf_sum, engine='xlsxwriter') as writer:
                                summary_matrix.to_excel(writer)
                            c_sum2.download_button("📊 Експорт Excel", buf_sum.getvalue(), f"zvedena_{grp_sum}.xlsx")
                        except:
                            c_sum2.warning("Для експорту в Excel встановіть бібліотеку xlsxwriter")
                    else:
                        st.warning("В базі даних не знайдено оцінок для вибраних предметів у цій групі.")
                except Exception as e:
                    st.error(f"Помилка бази даних: {e}")
                    st.info("Переконайтеся, що ви додали оцінки в 'Електронному журналі'.")
            else:
                st.error("Будь ласка, оберіть хоча б один предмет.")

def deanery_modules_view():
    st.title("Модулі Деканату")
    if st.session_state['role'] not in DEAN_LEVEL:
        st.error("У вас немає доступу до цієї панелі.")
        return

    conn = create_connection()
    c = conn.cursor()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔄 ЄДЕБО", "🛏️ Гуртожиток", "💰 Стипендія", "📜 Академ. Довідки", "📝 Інд. Відомості", "📄 Контракти"])

    with tab1:
        st.header("Єдина державна електронна база з питань освіти")
        col_ex, col_im = st.columns(2)
        with col_ex:
            st.subheader("📤 Експорт даних")
            format_type = st.radio("Формат експорту:", ["JSON", "XML (Beta)"])
            if st.button("Згенерувати файл для ЄДЕБО"):
                query = """SELECT s.full_name, s.group_name, u.role FROM students s LEFT JOIN users u ON s.full_name = u.full_name"""
                df_edebo = pd.read_sql(query, conn)
                if format_type == "JSON":
                    json_data = df_edebo.to_json(orient='records', force_ascii=False)
                    st.download_button(label="⬇️ Завантажити JSON", data=json_data, file_name=f"edebo_export_{datetime.now().date()}.json", mime="application/json")
                else:
                    xml_data = df_edebo.to_csv(index=False) 
                    st.download_button(label="⬇️ Завантажити XML/CSV", data=xml_data, file_name=f"edebo_export_{datetime.now().date()}.csv", mime="text/csv")
        with col_im:
            st.subheader("📥 Імпорт наказів")
            uploaded_edebo = st.file_uploader("Завантажте файл з ЄДЕБО (JSON/XML)", type=['json', 'xml'])
            if uploaded_edebo:
                st.success("Файл проаналізовано.")

    with tab2:
        st.header("Управління поселенням")
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("dorm_assign"):
                st.subheader("🏠 Поселення")
                all_students = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                student = st.selectbox("Студент", all_students)
                room = st.text_input("Номер кімнати", placeholder="Напр. 405-Б")
                paid = st.checkbox("Оплата за семестр внесена?")
                comment = st.text_area("Примітка (стан кімнати/інвентар)")
                if st.form_submit_button("Зберегти"):
                    status = "Оплачено" if paid else "Борг"
                    exists = c.execute("SELECT id FROM dormitory WHERE student_name=?", (student,)).fetchone()
                    if exists:
                        c.execute("UPDATE dormitory SET room_number=?, payment_status=?, comments=? WHERE student_name=?", (room, status, comment, student))
                        st.info("Дані оновлено!")
                    else:
                        c.execute("INSERT INTO dormitory (student_name, room_number, payment_status, comments) VALUES (?,?,?,?)", (student, room, status, comment))
                        st.success("Студента поселено!")
                    conn.commit()
                    st.rerun()
        with c2:
            st.subheader("📋 Списки мешканців")
            dorm_df = pd.read_sql("SELECT * FROM dormitory", conn)
            if not dorm_df.empty:
                def highlight_debt(val):
                    color = '#ff4b4b' if val == 'Борг' else '#00cc66'
                    return f'color: {color}'
                st.dataframe(dorm_df.style.map(highlight_debt, subset=['payment_status']), use_container_width=True)
            else: st.info("У гуртожитку поки ніхто не живе.")

    with tab3:
        st.header("Стипендіальна комісія")
        st.markdown("#### 📊 Автоматичний розрахунок рейтингу")
        if st.button("Оновити рейтинг успішності"):
            grade_query = "SELECT student_name, AVG(grade) as avg_score FROM grades GROUP BY student_name HAVING avg_score >= 4.0 ORDER BY avg_score DESC"
            rating_df = pd.read_sql(grade_query, conn)
            st.dataframe(rating_df, use_container_width=True)
            st.caption("*Показані студенти з балом 4.0 і вище")
        st.divider()
        col_schol1, col_schol2 = st.columns(2)
        with col_schol1:
            with st.form("add_scholarship"):
                st.subheader("Призначення стипендії")
                st_list = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                sch_student = st.selectbox("Студент", st_list, key="sch_st")
                sch_type = st.selectbox("Тип", ["Академічна (Звичайна)", "Академічна (Підвищена)", "Соціальна", "Президентська"])
                sch_amount = st.number_input("Сума (грн)", value=2000, step=100)
                if st.form_submit_button("Призначити"):
                    date_now = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO scholarship (student_name, type, amount, status, date_assigned) VALUES (?,?,?,?,?)", 
                              (sch_student, sch_type, sch_amount, "Активна", date_now))
                    conn.commit()
                    st.success("Стипендію призначено!")
                    st.rerun()
        with col_schol2:
            st.subheader("💰 Активні стипендіати")
            sch_df = pd.read_sql("SELECT student_name, type, amount, status, date_assigned FROM scholarship", conn)
            if not sch_df.empty:
                st.dataframe(sch_df, use_container_width=True)
                total_budget = sch_df[sch_df['status']=='Активна']['amount'].sum()
                st.metric("Місячний фонд стипендій", f"{total_budget} грн")
            else: st.info("Стипендій не призначено.")

    with tab4:
        st.header("Академічні довідки (Переведення)")
        st.info("Реєстрація довідок від студентів, що перевелися з інших ЗВО.")
        c_acad1, c_acad2 = st.columns(2)
        with c_acad1:
            with st.form("new_acad_cert"):
                st.subheader("➕ Нова довідка")
                st_list_a = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_name = st.selectbox("Студент", st_list_a)
                cert_num = st.text_input("Номер довідки")
                issue_dt = st.date_input("Дата видачі")
                source = st.text_input("Звідки видана (ЗВО/Факультет)")
                notes = st.text_area("Деталі (кредити, предмети)")
                if st.form_submit_button("Зареєструвати довідку"):
                    c.execute("INSERT INTO academic_certificates (student_name, cert_number, issue_date, source_institution, notes, added_by, added_date) VALUES (?,?,?,?,?,?,?)",
                              (s_name, cert_num, str(issue_dt), source, notes, st.session_state['full_name'], str(datetime.now().date())))
                    conn.commit()
                    st.success("Довідку додано!")
                    st.rerun()
        with c_acad2:
            st.subheader("🗂️ Реєстр довідок")
            df_certs = pd.read_sql("SELECT * FROM academic_certificates", conn)
            st.dataframe(df_certs, use_container_width=True)

    with tab5:
        st.header("Індивідуальні відомості")
        st.info("Формування відомостей для окремих випадків.")
        c_ind1, c_ind2 = st.columns(2)
        with c_ind1:
            with st.form("new_ind_statement"):
                st.subheader("📄 Створити відомість")
                st_list_i = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_ind = st.selectbox("Студент", st_list_i)
                subj_ind = st.selectbox("Дисципліна", SUBJECTS_LIST)
                type_ind = st.selectbox("Тип відомості", [
                    "На підвищення оцінки",
                    "Академічна різниця",
                    "Індивідуальний графік",
                    "Атестаційний лист екстерна",
                    "Позапланова дисципліна"
                ])
                reason = st.text_input("Підстава (№ розпорядження/заяви)")
                if st.form_submit_button("Сформувати"):
                    c.execute("INSERT INTO individual_statements (student_name, subject, statement_type, reason, date_issued, status, created_by) VALUES (?,?,?,?,?,?,?)",
                              (s_ind, subj_ind, type_ind, reason, str(datetime.now().date()), "Активна", st.session_state['full_name']))
                    conn.commit()
                    st.success(f"Відомість '{type_ind}' створено!")
                    st.rerun()
        with c_ind2:
            st.subheader("🗃️ Активні індивідуальні відомості")
            df_inds = pd.read_sql("SELECT * FROM individual_statements", conn)
            st.dataframe(df_inds, use_container_width=True)

    with tab6:
        st.header("Управління контрактами")
        st.info("Облік фінансових зобов'язань студентів контрактної форми навчання.")
        col_con1, col_con2 = st.columns([1, 2])
        with col_con1:
            with st.form("contract_form"):
                st.subheader("📝 Дані договору")
                st_list_c = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
                s_contract = st.selectbox("Студент", st_list_c)
                c_num = st.text_input("Номер договору")
                cd1, cd2 = st.columns(2)
                d_sign = cd1.date_input("Дата підписання")
                d_end = cd2.date_input("Термін дії до")
                cm1, cm2 = st.columns(2)
                amount_total = cm1.number_input("Загальна вартість (грн)", min_value=0.0, step=100.0)
                amount_paid = cm2.number_input("Сплачено (грн)", min_value=0.0, step=100.0)
                notes_c = st.text_area("Умови оплати / Примітки")
                calc_debt = amount_total - amount_paid
                status_c = "Сплачено повністю" if calc_debt <= 0 else f"Борг: {calc_debt} грн"
                if amount_paid == 0: status_c = "Не оплачено"
                if st.form_submit_button("Зберегти контракт"):
                    exists_c = c.execute("SELECT id FROM student_contracts WHERE student_name=? AND contract_number=?", (s_contract, c_num)).fetchone()
                    if exists_c:
                        c.execute("""UPDATE student_contracts SET 
                                     date_signed=?, end_date=?, total_amount=?, paid_amount=?, payment_status=?, notes=? 
                                     WHERE id=?""", 
                                     (str(d_sign), str(d_end), amount_total, amount_paid, status_c, notes_c, exists_c[0]))
                        st.success("Дані контракту оновлено!")
                    else:
                        c.execute("""INSERT INTO student_contracts 
                                     (student_name, contract_number, date_signed, end_date, total_amount, paid_amount, payment_status, notes) 
                                     VALUES (?,?,?,?,?,?,?,?)""",
                                     (s_contract, c_num, str(d_sign), str(d_end), amount_total, amount_paid, status_c, notes_c))
                        st.success("Новий контракт зареєстровано!")
                    conn.commit()
                    st.rerun()
        with col_con2:
            st.subheader("📂 Реєстр договорів")
            total_debt_query = "SELECT SUM(total_amount - paid_amount) FROM student_contracts WHERE total_amount > paid_amount"
            debt_sum = c.execute(total_debt_query).fetchone()[0]
            debt_sum = debt_sum if debt_sum else 0
            st.metric("Загальна заборгованість по факультету", f"{debt_sum:,.2f} грн")
            df_contracts = pd.read_sql("SELECT * FROM student_contracts", conn)
            if not df_contracts.empty:
                def highlight_debt_contract(val):
                    if isinstance(val, str) and "Борг" in val:
                        return 'color: #ff4b4b; font-weight: bold'
                    elif isinstance(val, str) and "Не оплачено" in val:
                        return 'color: #ff4b4b'
                    return 'color: #00cc66'
                st.dataframe(df_contracts.style.map(highlight_debt_contract, subset=['payment_status']), use_container_width=True)
                st.download_button("⬇️ Завантажити реєстр (CSV)", convert_df_to_csv(df_contracts), "contracts_registry.csv", "text/csv")
            else:
                st.info("Контрактів ще не додано.")

# --- НОВИЙ МОДУЛЬ: СЕСІЯ ТА РУХ КОНТИНГЕНТУ ---
def session_module_view():
    st.title("Сесія та Рух контингенту")
    if st.session_state['role'] not in DEAN_LEVEL:
        st.error("Доступ заборонено.")
        return

    conn = create_connection()
    c = conn.cursor()

    tab_session, tab_grading, tab_movement = st.tabs(["📑 Відомості (Сесія)", "✍️ Внесення оцінок", "🚀 Рух студентів"])

    # --- ВКЛАДКА 1: СТВОРЕННЯ ВІДОМОСТЕЙ ---
    with tab_session:
        st.header("Підготовка екзаменаційних відомостей")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            with st.form("create_sheet"):
                st.subheader("➕ Створити відомість")
                sheet_num = st.text_input("Номер відомості (№)")
                group_sel = st.selectbox("Група", list(GROUPS_DATA.keys()))
                subj_sel = st.selectbox("Дисципліна", SUBJECTS_LIST)
                control_type = st.selectbox("Тип контролю", ["Екзамен", "Залік", "Диференційований залік", "Перездача", "Комісія"])
                date_exam = st.date_input("Дата проведення")
                examiner = st.text_input("Екзаменатор", value=st.session_state['full_name'])
                
                if st.form_submit_button("Згенерувати відомість"):
                    if sheet_num:
                        c.execute("""INSERT INTO exam_sheets (sheet_number, group_name, subject, control_type, exam_date, examiner, status)
                                     VALUES (?,?,?,?,?,?,?)""", 
                                     (sheet_num, group_sel, subj_sel, control_type, str(date_exam), examiner, "Відкрита"))
                        conn.commit()
                        st.success(f"Відомість №{sheet_num} створена!")
                        st.rerun()
                    else:
                        st.warning("Вкажіть номер відомості.")

        with c2:
            st.subheader("📂 Журнал відомостей")
            sheets_df = pd.read_sql("SELECT * FROM exam_sheets ORDER BY id DESC", conn)
            st.dataframe(sheets_df, use_container_width=True)
            if not sheets_df.empty:
                st.download_button("⬇️ Завантажити реєстр відомостей", convert_df_to_csv(sheets_df), "exam_sheets.csv", "text/csv")

# --- ВКЛАДКА 2: ВНЕСЕННЯ ОЦІНОК ---
    with tab_grading:
        st.header("Занесення оцінок до бази даних")
        st.info("Оцінки, внесені тут, автоматично потрапляють у загальний журнал успішності та відомість.")
        
        sheets = pd.read_sql("SELECT id, sheet_number, group_name, subject, control_type FROM exam_sheets WHERE status='Відкрита'", conn)
        
        if not sheets.empty:
            sheet_options = sheets.apply(lambda x: f"№{x['sheet_number']} | {x['group_name']} | {x['subject']} ({x['control_type']})", axis=1).tolist()
            selected_sheet_str = st.selectbox("Оберіть активну відомість:", sheet_options)
            
            # Отримання даних обраної відомості
            sheet_idx = sheet_options.index(selected_sheet_str)
            sel_sheet_data = sheets.iloc[sheet_idx]
            
            curr_group = sel_sheet_data['group_name']
            curr_subj = sel_sheet_data['subject']
            curr_type = sel_sheet_data['control_type']
            
            st.markdown(f"**Група:** {curr_group} | **Предмет:** {curr_subj} | **Тип:** {curr_type}")
            
            students_list = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{curr_group}'", conn)['full_name'].tolist()
            existing_grades = pd.read_sql(f"SELECT student_name, grade FROM grades WHERE group_name='{curr_group}' AND subject='{curr_subj}' AND type_of_work='{curr_type}'", conn)
            
            data = []
            for student in students_list:
                found = existing_grades[existing_grades['student_name'] == student]
                grade = found.iloc[0]['grade'] if not found.empty else 0
                data.append({"Студент": student, "Оцінка": grade})
            
            df_grading = pd.DataFrame(data)
            st.write("Проставте оцінки у таблиці нижче:")

            # ВАЖЛИВО: Редактор та кнопка збереження мають бути ВСЕРЕДИНІ блоку if not sheets.empty
            edited_grades = st.data_editor(df_grading, use_container_width=True, key="editor_exam", hide_index=True)

            if st.button("💾 Зберегти оцінки в БД", key="save_exam_grades"):
                date_now = str(datetime.now().date())
                count_updated = 0
                
                for index, row in edited_grades.iterrows():
                    s_name = row['Студент']
                    s_grade = row['Оцінка']
                    
                    check = c.execute("SELECT id FROM grades WHERE student_name=? AND subject=? AND type_of_work=?", 
                                    (s_name, curr_subj, curr_type)).fetchone()
                    
                    if check:
                        c.execute("UPDATE grades SET grade=?, date=? WHERE id=?", (s_grade, date_now, check[0]))
                    else:
                        c.execute("INSERT INTO grades (student_name, group_name, subject, type_of_work, grade, date) VALUES (?,?,?,?,?,?)",
                                    (s_name, curr_group, curr_subj, curr_type, s_grade, date_now))
                    count_updated += 1
                
                conn.commit()
                st.success(f"Успішно збережено {count_updated} оцінок!")
                log_action(st.session_state['full_name'], "Exam Grading", f"Внесено оцінки: {curr_group}, {curr_subj}")
                st.rerun()
        else:
            st.warning("Немає відкритих відомостей. Спочатку створіть відомість у першій вкладці.")

    # --- ВКЛАДКА 3: РУХ КОНТИНГЕНТУ ---
    with tab_movement:
        st.header("Переведення на наступний навчальний рік")
        col_move1, col_move2 = st.columns(2)
        
        with col_move1:
            st.subheader("🔄 Переведення групи (курс +1)")
            move_group = st.selectbox("Оберіть групу", list(GROUPS_DATA.keys()), key="move_grp")
            
            match = re.match(r"(\d+)(.*)", move_group)
            next_name = move_group
            is_graduating = False
            
            if match:
                num, rest = int(match.group(1)), match.group(2)
                if num < 4: next_name = f"{num+1}{rest}"
                else:
                    next_name = f"Випуск-{move_group}"
                    is_graduating = True
            
            new_group_name = st.text_input("Нова назва групи:", value=next_name)
            
            if st.button("Виконати переведення"):
                if is_graduating:
                    students = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{move_group}'", conn)['full_name'].tolist()
                    for s in students:
                        c.execute("UPDATE student_education_info SET status='Випускник' WHERE student_name=?", (s,))
                        c.execute("UPDATE students SET group_name=? WHERE full_name=?", (new_group_name, s))
                else:
                    c.execute("UPDATE students SET group_name=? WHERE group_name=?", (new_group_name, move_group))
                    c.execute("UPDATE student_education_info SET course = course + 1 WHERE student_name IN (SELECT full_name FROM students WHERE group_name=?)", (new_group_name,))
                
                conn.commit()
                log_action(st.session_state['full_name'], "Group Move", f"{move_group} -> {new_group_name}")
                st.success("Переведення виконано!")
                st.rerun()

        with col_move2:
            st.subheader("🚫 Відрахування / Академвідпустка")
            action_type = st.selectbox("Дія", ["Відрахування", "Академвідпустка"])
            all_students = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
            student_to_action = st.selectbox("Студент", all_students, key="st_action")
            reason_move = st.text_input("Причина / № Наказу")
            
            if st.button("Застосувати"):
                status_map = {"Відрахування": "Відрахований", "Академвідпустка": "У академвідпустці"}
                new_status = status_map[action_type]
                c.execute("INSERT OR IGNORE INTO student_education_info (student_name) VALUES (?)", (student_to_action,))
                c.execute("UPDATE student_education_info SET status=? WHERE student_name=?", (new_status, student_to_action))
                
                if action_type == "Відрахування":
                    c.execute("DELETE FROM students WHERE full_name=?", (student_to_action,))
                
                conn.commit()
                log_action(st.session_state['full_name'], "Status Change", f"{student_to_action}: {new_status}")
                st.success("Статус змінено!")
                st.rerun()

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
                log_action(st.session_state['full_name'], "Role Change", f"Змінено роль {u_select} на {r_select}")
                st.success(f"Користувачу {u_select} призначено роль {r_select}")
                st.rerun()

    with t_logs:
        st.header("Журнал подій (Audit Log)")
        logs_df = pd.read_sql("SELECT * FROM system_logs ORDER BY id DESC", conn)
        
        col_fil1, col_fil2 = st.columns(2)
        filter_user = col_fil1.selectbox("Фільтр по користувачу", ["Всі"] + logs_df['user'].unique().tolist())
        filter_action = col_fil2.selectbox("Фільтр по дії", ["Всі"] + logs_df['action'].unique().tolist())
        
        if filter_user != "Всі":
            logs_df = logs_df[logs_df['user'] == filter_user]
        if filter_action != "Всі":
            logs_df = logs_df[logs_df['action'] == filter_action]
            
        st.dataframe(logs_df, use_container_width=True)
        st.download_button("⬇️ Завантажити лог (CSV)", convert_df_to_csv(logs_df), "system_logs.csv", "text/csv")


def main():
    # 1. Ініціалізація стану сесії
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # 2. Перевірка статусу авторизації
    if not st.session_state['logged_in']:
        # Показуємо сторінку входу, якщо користувач не зайшов
        login_register_page()
    else:
        # --- БОКОВА ПАНЕЛЬ (SIDEBAR) ---
        st.sidebar.title(f"👤 {st.session_state.get('full_name', 'Користувач')}")
        
        # Відображення ролі з відповідним стилем
        current_role = st.session_state.get('role', '').lower()
        if current_role == 'student':
            st.sidebar.markdown("### 🛡️ СТУДЕНТ (READ ONLY)")
        elif current_role == 'teacher':
            st.sidebar.markdown("### 👨‍🏫 ВИКЛАДАЧ (ACADEMIC)")
        elif current_role in DEAN_LEVEL:
            st.sidebar.markdown(f"### 🏛️ АДМІНІСТРАЦІЯ ({current_role.upper()})")
        else:
            st.sidebar.caption(f"Роль: {current_role.upper()}")
        
        # Кнопка зміни теми
        if st.sidebar.button("Змінити тему 🌓", use_container_width=True):
            toggle_theme()
            st.rerun()
            
        st.sidebar.divider()

        # 3. НАЛАШТУВАННЯ ДИНАМІЧНОГО МЕНЮ
        # Базове меню, доступне всім
        menu_options = {
            "🏠 Головна панель": main_panel,
            "👥 Студенти та групи": students_groups_view,
            "👨‍🏫 Викладачі": teachers_view,
            "📅 Розклад": schedule_view,
            "💯 Журнал оцінок": gradebook_view,
            "📝 Відвідуваність": attendance_view,
            "📂 Документообіг": documents_view,
            "🗄️ Репозиторій": file_repository_view,
            "📊 Звіти": reports_view
        }

        # Додавання модулів для Деканату (Admin/Dean)
        if current_role in DEAN_LEVEL:
            menu_options["🏛️ Модулі Деканату"] = deanery_modules_view
            menu_options["📉 Сесія та Рух"] = session_module_view

        # Додавання системних налаштувань лише для Admin
        if current_role == 'admin':
            menu_options["⚙️ Системні налаштування"] = system_settings_view

        # Створення списку для радіо-кнопки (додаємо Вихід у кінець)
        menu_list = list(menu_options.keys()) + ["🚪 Вийти з системи"]
        
        # 4. ЛОГІКА НАВІГАЦІЇ
        choice = st.sidebar.radio("Навігація", menu_list)

        if choice == "🚪 Вийти з системи":
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.session_state['role'] = None
            st.rerun()
        else:
            # Викликаємо функцію, яка відповідає вибору
            menu_options[choice]()

        # Футер бічної панелі
        st.sidebar.divider()
        st.sidebar.caption("Project Deanery .net v2.0 (Cloud)")

# --- ТОЧКА ВХОДУ ---
if __name__ == '__main__':
    main()
