# ui/auth.py
import streamlit as st
from database.db_core import create_connection, make_hashes

def perform_login(user, controller):
    st.session_state['logged_in'] = True
    st.session_state['username'] = user[0]
    st.session_state['role'] = user[2]
    st.session_state['full_name'] = user[3]
    controller.set('remember_user', user[0])
    st.rerun()

def login_register_page(controller):
    # Код вашої сторінки логіну
    # ...
