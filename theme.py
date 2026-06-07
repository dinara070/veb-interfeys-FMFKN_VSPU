import streamlit as st

MOBILE_CSS = """
<style>
@media (max-width: 768px) {
    .block-container { padding: 0.5rem 1rem !important; }
    [data-testid="stSidebar"] { min-width: 240px !important; }
    .stMetric { min-width: 0 !important; }
    .stDataFrame { font-size: 0.75rem !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    .stButton > button { width: 100% !important; margin-bottom: 4px; }
    [data-testid="column"] { min-width: 0 !important; }
}
@media (max-width: 480px) {
    [data-testid="stSidebar"] { display: none; }
    .hamburger-btn { display: block !important; }
}
/* Загальні покращення UI */
.stMetric { border-radius: 12px; padding: 12px; border: 1px solid rgba(128,128,128,0.15); }
.stButton > button { border-radius: 8px; transition: all 0.2s; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
[data-testid="stExpander"] { border-radius: 10px; }
div[data-testid="stTabs"] button { border-radius: 8px 8px 0 0; }
</style>
"""

DARK_CSS = """
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #1a1d26; border-right: 1px solid #2d2f3e; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #FFFFFF !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div,
    .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #262730 !important; color: #FFFFFF !important;
        border: 1px solid #3d3f4e !important;
    }
    input, textarea { color: #FFFFFF !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { color: #FFFFFF !important; }
    .streamlit-expanderHeader { background-color: #1a1d26 !important; color: #FFFFFF !important; }
    button { color: #FFFFFF !important; }
    .stMetric { background-color: #1a1d26 !important; border-color: #3d3f4e !important; }
</style>
"""

LIGHT_CSS = """
<style>
    .stApp { background-color: #f5f7fa; color: #1a1a2e; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e8eaf0; }
    h1, h2, h3, h4, h5, h6, p, li, span, label, .stMarkdown { color: #1a1a2e !important; }
    .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div,
    .stDateInput > div > div, .stNumberInput > div > div {
        background-color: #ffffff !important; color: #1a1a2e !important;
        border: 1px solid #d8dce8 !important;
    }
    input, textarea { color: #1a1a2e !important; }
    .stMetric { background-color: #ffffff !important; border-color: #e8eaf0 !important; }
</style>
"""


def init_theme():
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'


def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'


def apply_theme():
    # Завжди застосовуємо мобільний CSS + загальні покращення
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    if st.session_state.theme == 'dark':
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(LIGHT_CSS, unsafe_allow_html=True)
