import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import io
import altair as alt
import re  # Для логіки переведення курсів

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="LMS ФМФКН - Деканат", layout="wide", page_icon="🎓")

# --- ЛОГІКА ПЕРЕМИКАННЯ ТЕМИ ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

def toggle_theme():
    if st.session_state.theme == 'light':
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light'

# --- CSS СТИЛІ ---
dark_css = """
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #262730; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #FFFFFF !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div, .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #41444C !important; color: #FFFFFF !important;
    }
    input, textarea { color: #FFFFFF !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { color: #FFFFFF !important; }
    .streamlit-expanderHeader { background-color: #262730 !important; color: #FFFFFF !important; }
    button { color: #FFFFFF !important; }
</style>
"""

light_css = """
<style>
    .stApp { background-color: #FFFFFF; color: #000000; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #000000 !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div, .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #D3D3D3;
    }
    input, textarea { color: #000000 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { color: #000000 !important; }
    .streamlit-expanderHeader { background-color: #F0F2F6 !important; color: #000000 !important; }
    button { color: #000000 !important; }
</style>
"""

if st.session_state.theme == 'dark':
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)


# --- КОНСТАНТИ ТА ПРАВА ДОСТУПУ ---
ROLES_LIST = ["student", "starosta", "teacher", "methodist", "dean", "admin"]
TEACHER_LEVEL = ['teacher', 'methodist', 'dean', 'admin']
DEAN_LEVEL = ['methodist', 'dean', 'admin']

# --- СПИСОК ПРЕДМЕТІВ ---
SUBJECTS_LIST = [
    "Математичний аналіз", "Програмування", "Аналітична геометрія", "Дискретна математика", 
    "Фізика", "Англійська мова", "Філософія", "Числові системи", "Елементарна математика", 
    "Шкільний курс алгебри", "Шкільний курс геометрії", "Основи алгебри і дискретної математики", 
    "Лінійна алгебра і дискретна математика", "Вступ до спеціальності", "Основи статистики і аналізу даних", 
    "Експериментальна фізика", "Алгебра і теорія чисел", "Загальна психологія", "Інформатика", 
    "Основи структурного та об'єктно-орієнтованого програмування", "Загальна фізика", 
    "Методика виховної роботи", "Технології навчання фізики та інформатики", "Системи керування базами даних", 
    "Диференціальні рівняння", "Функціональний аналіз", "Бази даних та інформаційні системи", 
    "Методика навчання інформатики", "Методика навчання математики", "Алгоритми і структури даних", 
    "Основи педагогічної майстерності", "Теоретична фізика", "Інтегральні рівняння і варіаційне числення", 
    "Методика навчання фізики", "Методи обчислень", "Теорія і методика поглибленого навчання стереометрії", 
    "Фізика та методика її навчання у ліцеях", "Системи комп'ютерної математики", 
    "Теорія і практика математичних олімпіад", "Додаткові розділи геометрії", "Педагогіка і психологія вищої школи", 
    "Методологія та цифрові технології наукових досліджень у математиці", "Машинне навчання в освіті", 
    "Вибрані питання сучасної дидактики фізики", "Педагогіка і психологія профільної середньої освіти", 
    "Вибрані питання вищої математики", "Теорія і методика поглибленого навчання алгебри і початків аналізу", 
    "Астрофізика", "Цивільний захист", "Математичні моделі і моделі в освіті/педагогіці", 
    "Практикум з фізичного експерименту", "Статистичні методи обробки експериментальних даних", 
    "Основи теорії солітонів", "Ймовірнісно-статистичні методи досліджень", "Основи машинного навчання", 
    "Основи штучного інтелекту", "Загальна фізика. Оптика", "Практикум розв'язування задач з оптики", 
    "Практикум розв'язування олімпіадних задач з алгебри", "Основи теорії інтелектуальних систем"
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
    "4СОМ": ["Головата Марина Володимирівна", "Гріщенко Андрій Русланович", "Кліщ Юлія Сергіївна", "Мартинюк Анастасія Ігорівна", "Маховська Вікторія Юріївна", "Моцна Марія Анатоліївна", "Мруг Дарія Валентинівна", "Муляр Карина Сергіївна", "Неврюєва Дар'я Василівна", "Никитюк Юлія Ігорівна", "Павлова Вікторія Сергіївна", "Севастьянова Каріна Олегівна", "Струбчевська Дар'я Вячеславівна", "Тімощенко Ірина Романівна", "Фаштинська Марія Василівна", "Фурман Наталія Вікторівна", "Ходик Аліна Радіонівна", "Швець Наталія Юріївна"],
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
        "Коношевський Олег Леонідович (Завідувач кафедри)", "Матяш Ольга Іванівна", "Михайленко Любов Федорівна", "Воєвода Аліна Леонідівна (Декан факультету)",
        "Вотякова Леся Андріївна", "Калашніков Ігор В’ячеславович", "Наконечна Людмила Йосипівна", "Панасенко Олексій Борисович (Заступник декана)",
        "Тютюнник Діана Олегівна", "Комарова Карина Вадимівна"
    ],
    "Кафедра математики та інформатики": [
        "Ковтонюк Мар'яна Михайлівна (Завідувач кафедри)", "Бак Сергій Миколайович (Заступник декана)", "Клочко Оксана Віталіївна",
        "Граняк Валерій Федорович", "Ковтонюк Галина Миколаївна", "Косовець Олена Павлівна", "Крупський Ярослав Володимирович",
        "Соя Олена Миколаївна", "Тютюн Любов Андріївна", "Леонова Іванна Миколаївна", "Поліщук Віталій Олегович", "Ярош Оксана Іванівна"
    ],
    "Кафедра фізики і методики навчання фізики, астрономії": [
        "Сільвейстр Анатолій Миколайович (Завідувач кафедри)", "Заболотний Володимир Федорович", "Білюк Анатолій Іванович",
        "Думенко Вікторія Петрівна", "Моклюк Микола Олексійович", "Ксендзова Оксана Сергіївна", "Мамічева Інна Олексіївна",
        "Мороз Ярослав Олексійович", "Сіваєва Наталія Віталіївна", "Журжа Артем Арсенович"
    ]
}

# --- BACKEND ---
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

# --- СТОРІНКИ ---

def login_register_page():
    st.header("🔐 Вхід / Реєстрація (Адміністрація)")
    action = st.radio("Оберіть дію:", ["Вхід", "Реєстрація"], horizontal=True)
    conn = create_connection()
    c = conn.cursor()

    # Список дозволених ролей для реєстрації та входу
    ALLOWED_STAFF = ["admin", "dean"]

    if action == "Вхід":
        username = st.text_input("Логін")
        password = st.text_input("Пароль", type='password')
        if st.button("Увійти"):
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, make_hashes(password)))
            user = c.fetchone()
            if user:
                # Перевірка: вхід дозволено ТІЛЬКИ для admin та dean
                if user[2] not in ALLOWED_STAFF:
                    st.error("Доступ обмежено. Тільки для Адміністратора або Декана.")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user[0]
                    st.session_state['role'] = user[2]
                    st.session_state['full_name'] = user[3]
                    st.session_state['group'] = user[4]
                    log_action(user[3], "Login", f"Вхід системи: {user[2]}")
                    st.success(f"Вітаємо, {user[3]}!")
                    st.rerun()
            else:
                st.error("Невірний логін або пароль")

    elif action == "Реєстрація":
        st.info("Реєстрація доступна лише для Адміністрації та Деканату.")
        new_user = st.text_input("Вигадайте логін")
        new_pass = st.text_input("Вигадайте пароль", type='password')
        
        # Обмежений вибір ролей
        role = st.selectbox("Ваша посада", ALLOWED_STAFF)
        
        full_name = st.text_input("Ваше ПІБ (повністю)")
        group_link = "Staff/Admin"

        if st.button("Зареєструватися"):
            if new_user and new_pass and full_name:
                try:
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?)', 
                              (new_user, make_hashes(new_pass), role, full_name, group_link))
                    conn.commit()
                    log_action(full_name, "Registration", f"Новий запис: {role}")
                    st.success("Обліковий запис створено! Тепер увійдіть у вкладці 'Вхід'.")
                except sqlite3.IntegrityError:
                    st.error("Цей логін вже зайнятий.")
            else:
                st.warning("Будь ласка, заповніть усі поля.")

def main_panel():
    st.title("🏠 Головна панель LMS")
    st.markdown(f"### Вітаємо, {st.session_state['full_name']}!")
    conn = create_connection()
    
    st.divider()
    st.subheader("📊 Аналітика та Статистика")
    kpi1, kpi2, kpi3 = st.columns(3)
    
    if st.session_state['role'] in ['student', 'starosta']:
        my_group = st.session_state['group']
        group_count = pd.read_sql_query(f"SELECT count(*) FROM students WHERE group_name='{my_group}'", conn).iloc[0,0]
        kpi1.metric("Моя група", f"{group_count} студ.")
    else:
        total_students = pd.read_sql_query("SELECT count(*) FROM students", conn).iloc[0,0]
        kpi1.metric("Всього студентів", total_students)

    file_count = pd.read_sql_query("SELECT count(*) FROM file_storage", conn).iloc[0,0]
    kpi2.metric("Завантажено матеріалів", file_count)

    if st.session_state['role'] in ['student', 'starosta']:
        avg_q = f"SELECT avg(grade) FROM grades WHERE student_name='{st.session_state['full_name']}'"
    else:
        avg_q = "SELECT avg(grade) FROM grades"
    avg_val = pd.read_sql_query(avg_q, conn).iloc[0,0]
    avg_val = round(avg_val, 1) if avg_val else 0
    kpi3.metric("Середній бал", avg_val)

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**📈 Успішність (Середній бал)**")
        if st.session_state['role'] in ['student', 'starosta']:
            query_chart = f"SELECT subject, avg(grade) as avg_grade FROM grades WHERE student_name='{st.session_state['full_name']}' GROUP BY subject"
        else:
            query_chart = "SELECT subject, avg(grade) as avg_grade FROM grades GROUP BY subject"
        df_chart = pd.read_sql_query(query_chart, conn)
        if not df_chart.empty: st.bar_chart(df_chart.set_index('subject'))
        else: st.info("Наразі дані не завантажені.")

    with col_chart2:
        st.markdown("**📉 Відвідуваність**")
        q_att = f"SELECT status FROM attendance WHERE student_name='{st.session_state['full_name']}'" if st.session_state['role'] in ['student', 'starosta'] else "SELECT status FROM attendance"
        df_att = pd.read_sql_query(q_att, conn)
        if not df_att.empty:
            absent_count = df_att[df_att['status'] != ''].shape[0] 
            present_count = df_att[df_att['status'] == ''].shape[0] 
            att_data = pd.DataFrame({'Статус': ['Присутній', 'Відсутній/Інше'], 'Кількість': [present_count, absent_count]})
            base = alt.Chart(att_data).encode(theta=alt.Theta("Кількість", stack=True))
            pie = base.mark_arc(outerRadius=120).encode(color=alt.Color("Статус"), order=alt.Order("Кількість", sort="descending"), tooltip=["Статус", "Кількість"])
            st.altair_chart(pie, use_container_width=True)
        else: st.info("Наразі дані не завантажені.")

    st.divider()
    st.subheader("📢 Оголошення та Новини")
    # Додавати новини можуть TEACHER_LEVEL (Вчитель, Методист, Декан, Адмін)
    if st.session_state['role'] in TEACHER_LEVEL:
        with st.expander("📝 Додати нове оголошення"):
            with st.form("news_form"):
                n_title = st.text_input("Заголовок новини")
                n_msg = st.text_area("Текст оголошення")
                if st.form_submit_button("Опублікувати"):
                    if n_title and n_msg:
                        c = conn.cursor()
                        date_pub = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO news (title, message, author, date) VALUES (?,?,?,?)", (n_title, n_msg, st.session_state['full_name'], date_pub))
                        conn.commit()
                        st.success("Новину опубліковано!")
                        st.rerun()
    news_df = pd.read_sql_query("SELECT title, message, author, date FROM news ORDER BY id DESC", conn)
    if not news_df.empty:
        for i, row in news_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row['title']}")
                st.write(row['message'])
                st.caption(f"🗓️ {row['date']} | ✍️ {row['author']}")
    else: st.info("Наразі немає актуальних оголошень.")

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
    
    # Редагування: ТІЛЬКИ ДЕКАНАТ (DEAN_LEVEL) - Вчитель тут тільки читає
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

def teachers_view():
    st.title("👨‍🏫 Викладачі")
    for dept, teachers in TEACHERS_DATA.items():
        with st.expander(f"📚 {dept}"):
            for t in teachers: st.write(f"- {t}")

def schedule_view():
    st.title("📅 Розклад")
    conn = create_connection()
    grp = st.selectbox("Група", list(GROUPS_DATA.keys()))
    df = pd.read_sql_query(f"SELECT day, time, subject, teacher FROM schedule WHERE group_name='{grp}'", conn)
    if not df.empty: 
        st.download_button("⬇️ Завантажити", convert_df_to_csv(df), f"schedule_{grp}.csv", "text/csv")
        st.table(df)
    else: st.info("Наразі дані не завантажені.")
    
    # Редагування розкладу: ТІЛЬКИ ДЕКАНАТ (DEAN_LEVEL) - Вчитель тільки читає
    if st.session_state['role'] in DEAN_LEVEL:
        st.divider()
        with st.form("sch"):
            d = st.selectbox("День", ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"])
            t = st.selectbox("Час", ["08:30", "10:05", "11:40", "13:30", "15:00", "16:35"])
            s = st.text_input("Предмет")
            tch = st.text_input("Викладач", value=st.session_state['full_name'])
            if st.form_submit_button("Додати"):
                conn.execute("INSERT INTO schedule (group_name, day, time, subject, teacher) VALUES (?,?,?,?,?)", (grp, d, t, s, tch))
                conn.commit()
                st.rerun()

def documents_view():
    st.title("📂 Документообіг та Заяви")
    conn = create_connection()
    
    # Визначаємо доступні вкладки залежно від ролі (Для деканату додається "Обробка")
    tabs_list = ["📂 Реєстр / Мої заяви", "➕ Створити заяву", "📄 Шаблони заяв"]
    if st.session_state['role'] in DEAN_LEVEL:
        tabs_list.append("⚙️ Обробка запитів")
    
    tabs = st.tabs(tabs_list)

    # --- Вкладка 1: Реєстр ---
    with tabs[0]:
        st.subheader("Історія документів")
        
        # Логіка вибірки: Студент бачить своє, Деканат бачить все + фільтри
        if st.session_state['role'] in ['student', 'starosta']:
            query = f"SELECT id, title as 'Тип документу', status as 'Статус', date as 'Дата подачі' FROM documents WHERE student_name='{st.session_state['full_name']}' ORDER BY id DESC"
        else:
            c1, c2 = st.columns([1, 3])
            with c1:
                filter_status = st.selectbox("Фільтр за статусом", ["Всі", "Очікує", "Готово", "Відхилено"])
            
            base_q = "SELECT id, student_name as 'Студент', title as 'Тип документу', status as 'Статус', date as 'Дата' FROM documents"
            
            if filter_status != "Всі":
                # Фільтруємо по частині слова, щоб знайти "Готово (каб 102)"
                query = f"{base_q} WHERE status LIKE '{filter_status}%' ORDER BY id DESC"
            else:
                query = f"{base_q} ORDER BY id DESC"
        
        df_docs = pd.read_sql(query, conn)
        
        # Функція для розфарбовування статусів
        def color_status(val):
            color = ''
            if 'Очікує' in str(val): color = '#f0ad4e' # Orange
            elif 'Готово' in str(val): color = '#5cb85c' # Green
            elif 'Відхилено' in str(val): color = '#d9534f' # Red
            return f'color: {color}; font-weight: bold'
            
        if not df_docs.empty:
            st.dataframe(df_docs.style.map(color_status, subset=['Статус']), use_container_width=True)
        else:
            st.info("Список документів порожній")

    # --- Вкладка 2: Створити ---
    with tabs[1]:
        st.subheader("Подання нового запиту")
        with st.form("doc_create"):
            d_type = st.selectbox("Тип документу", [
                "Довідка про навчання (для ТЦК/Військкомату)",
                "Довідка про навчання (за місцем вимоги)",
                "Довідка про доходи (для субсидії/декларації)",
                "Виписка з оцінками (Transcript)",
                "Заява на матеріальну допомогу",
                "Заява на поселення в гуртожиток",
                "Заява на індивідуальний графік"
            ])
            d_comment = st.text_input("Додаткові примітки (напр. 'В ТЦК м. Вінниця' або 'Терміново')")
            
            if st.form_submit_button("Надіслати запит"):
                # Формуємо повну назву із коментарем
                full_title = f"{d_type}"
                if d_comment:
                    full_title += f" ({d_comment})"
                
                conn.execute("INSERT INTO documents (title, student_name, status, date) VALUES (?,?,?,?)", 
                             (full_title, st.session_state['full_name'], "Очікує", str(datetime.now().date())))
                conn.commit()
                st.success("Запит успішно надіслано до деканату! Відстежуйте статус у першій вкладці.")
                st.rerun()

    # --- Вкладка 3: Шаблони ---
    with tabs[2]:
        st.subheader("Бланки та зразки заяв")
        st.caption("Завантажте, роздрукуйте та підпишіть, якщо потрібна паперова копія.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("📄 **Заява на вступ**")
                st.caption("Для абітурієнтів")
                st.download_button("⬇️ Завантажити DOCX", b"template_data", "zayava_vstup.docx", key="dl1")
        with c2:
            with st.container(border=True):
                st.markdown("📄 **Заява на гуртожиток**")
                st.caption("Ордер на поселення")
                st.download_button("⬇️ Завантажити PDF", b"template_data", "gurtozhitok.pdf", key="dl2")
        with c3:
            with st.container(border=True):
                st.markdown("📄 **Обхідний лист**")
                st.caption("Для випускників")
                st.download_button("⬇️ Завантажити PDF", b"template_data", "obhidniy.pdf", key="dl3")

    # --- Вкладка 4: Обробка (Тільки Деканат) ---
    if st.session_state['role'] in DEAN_LEVEL:
        with tabs[3]:
            st.subheader("⚙️ Обробка запитів студентів")
            
            # Отримуємо тільки ті, що мають статус "Очікує"
            pending_docs = pd.read_sql("SELECT id, student_name, title, date FROM documents WHERE status='Очікує'", conn)
            
            if not pending_docs.empty:
                st.warning(f"Увага! Необроблених запитів: {len(pending_docs)}")
                
                col_sel, col_act = st.columns([1, 2])
                
                with col_sel:
                    # Вибір запиту для обробки
                    req_id = st.selectbox("Оберіть запит", pending_docs['id'].tolist(), format_func=lambda x: f"ID {x}")
                
                # Отримуємо дані обраного запиту
                sel_row = pending_docs[pending_docs['id']==req_id].iloc[0]
                
                with col_act:
                    with st.container(border=True):
                        st.markdown(f"**Студент:** {sel_row['student_name']}")
                        st.markdown(f"**Запит:** {sel_row['title']}")
                        st.markdown(f"**Дата:** {sel_row['date']}")
                        st.divider()
                        
                        ac1, ac2 = st.columns(2)
                        new_status = ac1.selectbox("Рішення", ["Готово", "Відхилено", "В роботі"])
                        admin_comment = ac2.text_input("Коментар для студента", placeholder="Напр. 'Заберіть у 205 каб.'")
                        
                        if st.button("✅ Застосувати рішення"):
                            final_status = new_status
                            if admin_comment:
                                final_status += f" ({admin_comment})"
                            
                            conn.execute("UPDATE documents SET status=? WHERE id=?", (final_status, req_id))
                            conn.commit()
                            st.success(f"Статус запиту #{req_id} змінено на '{final_status}'")
                            st.rerun()
            else:
                st.success("🎉 Чудова робота! Всі нові запити опрацьовано.")

def file_repository_view():
    st.title("🗄️ Файловий Репозиторій")
    conn = create_connection()
    c = conn.cursor()
    col_f1, col_f2 = st.columns([2,1])
    with col_f1: filter_subj = st.selectbox("📂 Фільтр по предмету", ["Всі"] + SUBJECTS_LIST)
    
    # Завантаження файлів: ВЧИТЕЛЬ + ДЕКАНАТ (TEACHER_LEVEL)
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

def gradebook_view():
    st.title("💯 Журнал Оцінок")
    conn = create_connection()
    c = conn.cursor()
    # СТУДЕНТ ТА СТАРОСТА ТІЛЬКИ ЧИТАЮТЬ
    if st.session_state['role'] in ['student', 'starosta']:
        df = pd.read_sql(f"SELECT subject, type_of_work, grade, date FROM grades WHERE student_name='{st.session_state['full_name']}'", conn)
        st.dataframe(df, use_container_width=True)
    else:
        # ВЧИТЕЛЬ ТА ДЕКАНАТ РЕДАГУЮТЬ
        t_journal, t_ops = st.tabs(["Журнал", "📥/📤 Операції"])
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Група", list(GROUPS_DATA.keys()))
        subj = c2.selectbox("Предмет", SUBJECTS_LIST)
        with t_journal:
            with st.expander("➕ Додати колонку"):
                with st.form("new_col"):
                    nm = st.text_input("Назва")
                    dt = st.date_input("Дата")
                    if st.form_submit_button("Створити"):
                        stds = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{grp}'", conn)['full_name'].tolist()
                        for s in stds:
                            c.execute("INSERT INTO grades (student_name, group_name, subject, type_of_work, grade, date) VALUES (?,?,?,?,?,?)", (s, grp, subj, nm, 0, str(dt)))
                        conn.commit()
                        st.rerun()
            raw = pd.read_sql(f"SELECT student_name, type_of_work, grade FROM grades WHERE group_name='{grp}' AND subject='{subj}'", conn)
            if not raw.empty:
                matrix = raw.pivot_table(index='student_name', columns='type_of_work', values='grade', aggfunc='first').fillna(0)
                edited = st.data_editor(matrix, use_container_width=True)
                if st.button("Зберегти зміни"):
                    changes_made = False
                    for s_name, row in edited.iterrows():
                        for w_name, val in row.items():
                            old_row = c.execute("SELECT id, grade FROM grades WHERE student_name=? AND subject=? AND type_of_work=?", (s_name, subj, w_name)).fetchone()
                            if old_row:
                                old_grade = old_row[1]
                                if old_grade != val:
                                    c.execute("UPDATE grades SET grade=? WHERE id=?", (val, old_row[0]))
                                    log_action(st.session_state['full_name'], "Grade Update", f"{s_name} | {subj} | {w_name}: {old_grade} -> {val}")
                                    changes_made = True
                    conn.commit()
                    if changes_made:
                        st.success("Збережено та залоговано!")
                    else:
                        st.info("Змін не виявлено.")
            else: st.info("Додайте колонку.")
        with t_ops:
            raw_export = pd.read_sql(f"SELECT * FROM grades WHERE group_name='{grp}' AND subject='{subj}'", conn)
            st.download_button("⬇️ Експорт (Raw)", convert_df_to_csv(raw_export), "grades_raw.csv", "text/csv")
            if not raw.empty: st.download_button("⬇️ Експорт (Matrix)", convert_df_to_csv(matrix), "grades_matrix.csv", "text/csv")
            
            up_grades = st.file_uploader("Імпорт оцінок (CSV)", type="csv")
            if up_grades and st.button("Імпортувати"):
                try:
                    df_new = pd.read_csv(up_grades)
                    df_new.to_sql('grades', conn, if_exists='append', index=False)
                    st.success("Імпортовано!")
                    st.rerun()
                except Exception as e: st.error(f"Помилка: {e}")

def attendance_view():
    st.title("📝 Журнал Відвідуваності")
    conn = create_connection()
    # СТУДЕНТ ТІЛЬКИ ЧИТАЄ
    if st.session_state['role'] == 'student':
        df_att = pd.read_sql(f"SELECT subject, date_column as 'Дата', status FROM attendance WHERE student_name='{st.session_state['full_name']}'", conn)
        st.dataframe(df_att, use_container_width=True)
    else:
        # Староста/Викладач/Деканат редагують
        c1, c2 = st.columns(2)
        grp = c1.selectbox("Група", list(GROUPS_DATA.keys()), key="att_grp")
        subj = c2.selectbox("Предмет", SUBJECTS_LIST, key="att_sbj")
        with st.expander("➕ Додати дату"):
            with st.form("new_att_col"):
                col_name = st.text_input("Назва")
                if st.form_submit_button("Створити"):
                    stds = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{grp}'", conn)['full_name'].tolist()
                    for s in stds:
                        conn.execute("INSERT INTO attendance (student_name, group_name, subject, date_column, status) VALUES (?,?,?,?,?)", (s, grp, subj, col_name, "")) 
                    conn.commit()
                    st.rerun()
        raw = pd.read_sql(f"SELECT student_name, date_column, status FROM attendance WHERE group_name='{grp}' AND subject='{subj}'", conn)
        if not raw.empty:
            matrix = raw.pivot_table(index='student_name', columns='date_column', values='status', aggfunc='first').fillna("")
            st.write("Ставте 'н' для відсутніх:")
            edited = st.data_editor(matrix, use_container_width=True)
            if st.button("💾 Зберегти"):
                for s_name, row in edited.iterrows():
                    for d_col, val in row.items():
                        exists = conn.execute("SELECT id FROM attendance WHERE student_name=? AND subject=? AND date_column=?", (s_name, subj, d_col)).fetchone()
                        if exists: conn.execute("UPDATE attendance SET status=? WHERE id=?", (val, exists[0]))
                conn.commit()
                st.success("Збережено!")
        else: st.info("Наразі дані не завантажені.")

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
            st.download_button("⬇️ Завантажити відомість", convert_df_to_csv(matrix), f"vidomist_{grp}_{subj}.csv", "text/csv")
        else: st.warning("Наразі дані не завантажені.")

    with t2:
        st.subheader("Електронна Анкета Студента")
        all_students = pd.read_sql("SELECT full_name FROM students", conn)
        if not all_students.empty:
            selected_student = st.selectbox("Оберіть студента", all_students['full_name'].tolist())
            tab_main, tab_edu, tab_prev_edu, tab_grades = st.tabs(["Загальна", "Навчання (Поточне)", "Освіта (До вступу)", "Успішність"])
            
            with tab_main:
                info = pd.read_sql(f"SELECT * FROM students WHERE full_name='{selected_student}'", conn)
                st.write("**Основні дані:**")
                st.dataframe(info, use_container_width=True)

            with tab_edu:
                edu_data = pd.read_sql(f"SELECT * FROM student_education_info WHERE student_name='{selected_student}'", conn)
                d = edu_data.iloc[0].to_dict() if not edu_data.empty else {}
                disabled = st.session_state['role'] not in DEAN_LEVEL
                with st.form("edu_form"):
                    c1, c2, c3 = st.columns(3)
                    status = c1.selectbox("Стан", ["Навчається", "У академвідпустці", "Відрахований", "Випускник"], index=0 if 'status' not in d else ["Навчається", "У академвідпустці", "Відрахований", "Випускник"].index(d.get('status', 'Навчається')), disabled=disabled)
                    form_edu = c2.selectbox("Форма навчання", ["Денна", "Заочна"], index=0 if d.get('study_form') != "Заочна" else 1, disabled=disabled)
                    course = c3.number_input("Курс", min_value=1, max_value=6, value=d.get('course', 1), disabled=disabled)
                    c4, c5 = st.columns(2)
                    faculty = c4.text_input("Факультет", value=d.get('faculty', "ФМФКН"), disabled=disabled)
                    specialty = c5.text_input("Спеціальність / ОПП", value=d.get('edu_program', ""), disabled=disabled)
                    is_contract = st.checkbox("Контракт", value=(d.get('is_contract') == 'True'), disabled=disabled)
                    st.divider()
                    st.markdown("Накази")
                    c9, c10, c11 = st.columns(3)
                    enr_ord = c9.text_input("№ Наказу зарахування", value=d.get('enroll_order_num', ""), disabled=disabled)
                    enr_date = c10.text_input("Дата зарахування", value=d.get('enroll_date', ""), disabled=disabled)
                    stud_id = c11.text_input("Студентський квиток", value=d.get('student_id_card', ""), disabled=disabled)

                    if not disabled:
                        if st.form_submit_button("Зберегти (Навчання)"):
                            last_mod = datetime.now().strftime("%Y-%m-%d %H:%M")
                            exists = c.execute(f"SELECT student_name FROM student_education_info WHERE student_name='{selected_student}'").fetchone()
                            if exists:
                                c.execute("UPDATE student_education_info SET status=?, study_form=?, course=?, is_contract=?, faculty=?, specialty=?, edu_program=?, enroll_order_num=?, enroll_date=?, student_id_card=?, last_modified=? WHERE student_name=?", (status, form_edu, course, str(is_contract), faculty, specialty, specialty, enr_ord, enr_date, stud_id, last_mod, selected_student))
                            else:
                                c.execute("INSERT INTO student_education_info (student_name, status, study_form, course, is_contract, faculty, specialty, edu_program, enroll_order_num, enroll_date, student_id_card, last_modified) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (selected_student, status, form_edu, course, str(is_contract), faculty, specialty, specialty, enr_ord, enr_date, stud_id, last_mod))
                            conn.commit()
                            st.success("Дані збережено!")
                            st.rerun()

            with tab_prev_edu:
                st.markdown("### Документ про освіту (вступний)")
                prev_data = pd.read_sql(f"SELECT * FROM student_prev_education WHERE student_name='{selected_student}'", conn)
                p = prev_data.iloc[0].to_dict() if not prev_data.empty else {}
                disabled_prev = st.session_state['role'] not in DEAN_LEVEL
                
                with st.form("prev_edu_form"):
                    c_p1, c_p2 = st.columns(2)
                    inst_name = c_p1.text_input("Назва навчального закладу", value=p.get('institution_name', ""), disabled=disabled_prev)
                    inst_type = c_p2.selectbox("Тип закладу", ["Школа", "Ліцей", "Коледж", "Технікум", "Університет"], index=0 if 'institution_type' not in p else ["Школа", "Ліцей", "Коледж", "Технікум", "Університет"].index(p.get('institution_type', 'Школа')), disabled=disabled_prev)
                    
                    st.markdown("#### Диплом / Атестат")
                    c_d1, c_d2, c_d3 = st.columns(3)
                    dip_type = c_d1.text_input("Тип документу", value=p.get('diploma_type', "Атестат"), disabled=disabled_prev)
                    dip_ser = c_d2.text_input("Серія", value=p.get('diploma_series', ""), disabled=disabled_prev)
                    dip_num = c_d3.text_input("Номер", value=p.get('diploma_number', ""), disabled=disabled_prev)
                    dip_grades = st.text_area("Оцінки з додатку (Короткий зміст)", value=p.get('diploma_grades_summary', ""), disabled=disabled_prev)
                    
                    st.markdown("#### Інше")
                    langs = st.text_input("Іноземні мови (вивчав до вступу)", value=p.get('foreign_languages', "Англійська"), disabled=disabled_prev)
                    
                    if not disabled_prev:
                        if st.form_submit_button("Зберегти (Освіта)"):
                            last_mod_p = datetime.now().strftime("%Y-%m-%d %H:%M")
                            exists_p = c.execute(f"SELECT student_name FROM student_prev_education WHERE student_name='{selected_student}'").fetchone()
                            if exists_p:
                                c.execute("""UPDATE student_prev_education SET 
                                    institution_name=?, institution_type=?, diploma_type=?, diploma_series=?, diploma_number=?,
                                    diploma_grades_summary=?, foreign_languages=?, last_modified=?
                                    WHERE student_name=?""",
                                    (inst_name, inst_type, dip_type, dip_ser, dip_num, dip_grades, langs, last_mod_p, selected_student))
                            else:
                                c.execute("""INSERT INTO student_prev_education (
                                    student_name, institution_name, institution_type, diploma_type, diploma_series, diploma_number,
                                    diploma_grades_summary, foreign_languages, last_modified
                                ) VALUES (?,?,?,?,?,?,?,?,?)""",
                                (selected_student, inst_name, inst_type, dip_type, dip_ser, dip_num, dip_grades, langs, last_mod_p))
                            conn.commit()
                            st.success("Дані про освіту збережено!")
                            st.rerun()

            with tab_grades:
                grades = pd.read_sql(f"SELECT subject, type_of_work, grade, date FROM grades WHERE student_name='{selected_student}'", conn)
                if not grades.empty:
                    st.dataframe(grades, use_container_width=True)
                    st.metric("Середній бал", f"{grades['grade'].mean():.2f}")
                else: st.info("Оцінок немає.")
                
        else: st.error("Наразі дані не завантажені.")

    with t3:
        st.subheader("Генератор Зведеної Відомості")
        grp_sum = st.selectbox("Оберіть групу", list(GROUPS_DATA.keys()), key="rep_sum_grp")
        available_subjects_query = f"SELECT DISTINCT subject FROM grades WHERE group_name='{grp_sum}'"
        available_subjects = pd.read_sql(available_subjects_query, conn)['subject'].tolist()
        if not available_subjects: available_subjects = SUBJECTS_LIST
        selected_subjects = st.multiselect("Оберіть предмети для відомості", options=available_subjects, default=available_subjects)
        
        if st.button("🔄 Згенерувати таблицю"):
            if selected_subjects:
                subjects_placeholder = "'" + "','".join(selected_subjects) + "'"
                query = f"""SELECT student_name, subject, AVG(grade) as final_grade FROM grades WHERE group_name='{grp_sum}' AND subject IN ({subjects_placeholder}) GROUP BY student_name, subject"""
                data = pd.read_sql(query, conn)
                if not data.empty:
                    summary_matrix = data.pivot_table(index='student_name', columns='subject', values='final_grade').fillna(0).round(0).astype(int)
                    all_students_df = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{grp_sum}'", conn)
                    summary_matrix = all_students_df.merge(summary_matrix, left_on='full_name', right_index=True, how='left').fillna(0)
                    summary_matrix.set_index('full_name', inplace=True)
                    st.success(f"Згенеровано відомість для групи {grp_sum}")
                    st.dataframe(summary_matrix, use_container_width=True)
                    st.download_button(label="⬇️ Завантажити таблицю (CSV)", data=convert_df_to_csv(summary_matrix), file_name=f"zvedena_vidomist_{grp_sum}.csv", mime="text/csv")
                else: st.warning("Для обраних предметів оцінки відсутні.")
            else: st.error("Будь ласка, оберіть хоча б один предмет.")

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
        
        # Вибір відомості
        sheets = pd.read_sql("SELECT id, sheet_number, group_name, subject, control_type FROM exam_sheets WHERE status='Відкрита'", conn)
        
        if not sheets.empty:
            sheet_options = sheets.apply(lambda x: f"№{x['sheet_number']} | {x['group_name']} | {x['subject']} ({x['control_type']})", axis=1)
            selected_sheet_str = st.selectbox("Оберіть активну відомість:", sheet_options)
            
            # Отримання даних обраної відомості
            sheet_idx = sheet_options[sheet_options == selected_sheet_str].index[0]
            sel_sheet_data = sheets.iloc[sheet_idx]
            
            curr_group = sel_sheet_data['group_name']
            curr_subj = sel_sheet_data['subject']
            curr_type = sel_sheet_data['control_type']
            
            st.markdown(f"**Група:** {curr_group} | **Предмет:** {curr_subj} | **Тип:** {curr_type}")
            
            # Отримання студентів
            students_list = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{curr_group}'", conn)['full_name'].tolist()
            
            # Отримання існуючих оцінок з таблиці GRADES
            existing_grades = pd.read_sql(f"""SELECT student_name, grade FROM grades 
                                              WHERE group_name='{curr_group}' AND subject='{curr_subj}' AND type_of_work='{curr_type}'""", conn)
            
            # Формування DF для редагування
            data = []
            for student in students_list:
                grade = 0
                found = existing_grades[existing_grades['student_name'] == student]
                if not found.empty:
                    grade = found.iloc[0]['grade']
                data.append({"Студент": student, "Оцінка": grade})
            
            df_grading = pd.DataFrame(data)
            
            st.write("Проставте оцінки у таблиці нижче:")
            edited_grades = st.data_editor(df_grading, use_container_width=True)
            
            if st.button("💾 Зберегти оцінки в БД"):
                date_now = str(datetime.now().date())
                count_updated = 0
                
                for index, row in edited_grades.iterrows():
                    s_name = row['Студент']
                    s_grade = row['Оцінка']
                    
                    check = c.execute(f"""SELECT id FROM grades 
                                          WHERE student_name=? AND subject=? AND type_of_work=?""", 
                                          (s_name, curr_subj, curr_type)).fetchone()
                    
                    if check:
                        c.execute("UPDATE grades SET grade=?, date=? WHERE id=?", (s_grade, date_now, check[0]))
                    else:
                        c.execute("""INSERT INTO grades (student_name, group_name, subject, type_of_work, grade, date)
                                     VALUES (?,?,?,?,?,?)""", (s_name, curr_group, curr_subj, curr_type, s_grade, date_now))
                    count_updated += 1
                
                conn.commit()
                st.success(f"Успішно збережено {count_updated} оцінок!")
                log_action(st.session_state['full_name'], "Exam Grading", f"Внесено оцінки по відомості для {curr_group}, {curr_subj}")
        
        else:
            st.warning("Немає відкритих відомостей. Створіть нову у вкладці 'Відомості'.")

    # --- ВКЛАДКА 3: РУХ КОНТИНГЕНТУ ---
    with tab_movement:
        st.header("Переведення на наступний навчальний рік")
        
        col_move1, col_move2 = st.columns(2)
        
        with col_move1:
            st.subheader("🔄 Переведення групи (курс +1)")
            move_group = st.selectbox("Оберіть групу для переведення", list(GROUPS_DATA.keys()), key="move_grp")
            
            next_name = move_group
            match = re.match(r"(\d+)(.*)", move_group)
            is_graduating = False
            
            if match:
                num = int(match.group(1))
                rest = match.group(2)
                if num < 4:
                    next_name = f"{num+1}{rest}"
                else:
                    next_name = f"Випуск-{move_group}"
                    is_graduating = True
            
            new_group_name = st.text_input("Нова назва групи:", value=next_name)
            
            if st.button("Виконати переведення"):
                if is_graduating:
                    students_to_grad = pd.read_sql(f"SELECT full_name FROM students WHERE group_name='{move_group}'", conn)['full_name'].tolist()
                    for s in students_to_grad:
                        c.execute("UPDATE student_education_info SET status='Випускник' WHERE student_name=?", (s,))
                        c.execute("UPDATE students SET group_name=? WHERE full_name=?", (new_group_name, s))
                    st.success(f"Група {move_group} випущена! Статус студентів оновлено.")
                else:
                    c.execute("UPDATE students SET group_name=? WHERE group_name=?", (new_group_name, move_group))
                    c.execute(f"UPDATE student_education_info SET course = course + 1 WHERE student_name IN (SELECT full_name FROM students WHERE group_name=?)", (new_group_name,))
                    st.success(f"Групу {move_group} переведено в {new_group_name}!")
                
                conn.commit()
                log_action(st.session_state['full_name'], "Group Move", f"Переведено групу {move_group} -> {new_group_name}")
                st.rerun()

        with col_move2:
            st.subheader("🚫 Відрахування / Академвідпустка")
            action_type = st.selectbox("Дія", ["Відрахування", "Академвідпустка"])
            
            all_students_m = pd.read_sql("SELECT full_name FROM students", conn)['full_name'].tolist()
            student_to_action = st.selectbox("Студент", all_students_m, key="st_action")
            reason_move = st.text_input("Причина / № Наказу")
            
            if st.button("Застосувати"):
                status_map = {"Відрахування": "Відрахований", "Академвідпустка": "У академвідпустці"}
                new_status = status_map[action_type]
                
                c.execute("INSERT OR IGNORE INTO student_education_info (student_name) VALUES (?)", (student_to_action,))
                c.execute("UPDATE student_education_info SET status=? WHERE student_name=?", (new_status, student_to_action))
                
                if action_type == "Відрахування":
                    c.execute("DELETE FROM students WHERE full_name=?", (student_to_action,))
                    st.warning(f"Студента {student_to_action} відраховано та видалено зі списків.")
                else:
                    st.info(f"Статус студента {student_to_action} змінено на '{new_status}'.")
                
                conn.commit()
                log_action(st.session_state['full_name'], "Student Status Change", f"{student_to_action}: {new_status} ({reason_move})")
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
    init_db()
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['role'] = None
        st.session_state['full_name'] = ""

    if not st.session_state['logged_in']:
        login_register_page()
    else:
        st.sidebar.title(f"👤 {st.session_state['full_name']}")
        role_upper = st.session_state['role'].upper()
        if st.session_state['role'] == 'student':
             st.sidebar.markdown("### 🛡️ СТУДЕНТ (READ ONLY)")
        elif st.session_state['role'] == 'teacher':
             st.sidebar.markdown("### 👨‍🏫 ВИКЛАДАЧ (ACADEMIC)")
        else:
             st.sidebar.caption(f"Роль: {role_upper}")
        
        if st.sidebar.button("Перемкнути тему 🌓"):
            toggle_theme()
            st.rerun()
            
        st.sidebar.divider()
        
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
        
        if st.session_state['role'] in DEAN_LEVEL:
            menu_options["Модулі Деканату"] = deanery_modules_view
            menu_options["Сесія та Рух"] = session_module_view 
        
        if st.session_state['role'] == 'admin':
            menu_options["Системні налаштування"] = system_settings_view

        selection = st.sidebar.radio("Навігація", list(menu_options.keys()))
        menu_options[selection]()
        
        st.sidebar.divider()
        if st.sidebar.button("Вийти 🚪"):
            st.session_state['logged_in'] = False
            st.rerun()

if __name__ == '__main__':
    main()
