import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO

# --- CONFIGURACIÓN GENERAL ---
# URL de tu aplicación (IMPORTANTE: Sin corchetes ni paréntesis extraños)
BASE_URL = "[https://registro-ciudadano-app.streamlit.app](https://registro-ciudadano-app.streamlit.app)"

# Configuración de la página
st.set_page_config(
    page_title="Formulario de Registro Ciudadano",
    page_icon="🗳️",
    layout="centered"
)

# Estilos visuales
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1 { color: #0f3460; text-align: center; }
    .stButton>button { width: 100%; background-color: #0f3460; color: white; }
    .stSuccess { background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)
