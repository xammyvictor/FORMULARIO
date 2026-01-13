import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO
import re
import requests

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
API_KEY = "" # El entorno proporciona la clave automáticamente

st.set_page_config(
    page_title="Formulario de Registro - IA Electoral",
    page_icon="🗳️",
    layout="centered"
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #333333 !important; }
    h1, h2, h3 { color: #D81B60 !important; text-align: center; font-family: 'Helvetica'; }
    .stButton>button { 
        width: 100%; background-color: #E91E63 !important; color: white !important; 
        border-radius: 8px; font-weight: bold;
    }
    .stButton>button:hover { background-color: #C2185B !important; }
    [data-testid="stSidebar"] { background-color: #FCE4EC !important; }
    input:disabled { background-color: #f8f9fa !important; color: #495057 !important; border: 1px solid #dee2e6 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE IA Y BÚSQUEDA ---

def consultar_puesto_ia(cedula, barrio, ciudad):
    """
    Usa la API de Gemini con búsqueda en Google para encontrar el puesto de votación.
    """
    try:
        system_prompt = "Eres un asistente experto en el sistema electoral colombiano. Tu tarea es identificar el puesto de votación oficial o más cercano para un ciudadano."
        user_query = f"¿Cuál es el puesto de votación asignado en Colombia para un ciudadano que vive en el barrio {barrio} de la ciudad {ciudad}? Responde únicamente con el NOMBRE DEL LUGAR Y LA DIRECCIÓN. Si no lo encuentras, sugiere el colegio público más cercano."
        
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "tools": [{"google_search": {}}]
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return text.strip() if text else "Puesto no determinado"
        return "Consulta manual requerida"
    except Exception:
        return "Error en consulta de IA"

def validar_cedula_real(cedula_str):
    """
    Valida que la cédula sea un número entre 7 y 10 dígitos (estándar colombiano).
    Se elimina la validación de DV matemático para permitir cédulas reales.
    """
    return bool(re.match(r'^\d{7,10}$', cedula_str))

# --- CONEXIÓN A DRIVE ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error de credenciales: {e}")
        return None

def save_and_learn(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        ws_reg = sh.sheet1
        
        # Guardar en Hoja Principal
        row = [
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.user_name,
            data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"],
            data_dict["ciudad"], data_dict["lugar_votacion"]
        ]
        ws_reg.append_row(row)
        
        # Alimentar base de datos de consulta rápida
        try:
            ws_lugares = sh.worksheet("Lugares_Votacion")
        except gspread.WorksheetNotFound:
            ws_lugares = sh.add_worksheet(title="Lugares_Votacion", rows="100", cols="4")
            ws_lugares.append_row(["Barrio", "Ciudad", "Lugar_Votacion", "Fecha"])
        
        ws_lugares.append_row([data_dict["barrio"], data_dict["ciudad"], data_dict["lugar_votacion"], row[0]])
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- SESIÓN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = "invitado"

if not st.session_state.logged_in:
    st.title("🔐 Acceso")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            if p == "1234":
                st.session_state.logged_in = True
                st.session_state.user_name = u
                st.rerun()
    st.stop()

# --- FORMULARIO ---
st.title("🗳️ Maria Irma - Registro")

if "lugar_detectado" not in st.session_state: st.session_state.lugar_detectado = ""

with st.form("main_form"):
    st.markdown("### Datos de Identificación")
    col_id1, col_id2 = st.columns([1, 1])
    with col_id1:
        cedula = st.text_input("Número de Cédula (7 a 10 dígitos)")
    with col_id2:
        nombre = st.text_input("Nombre Completo").upper()

    st.markdown("---")
    st.markdown("### Ubicación y Contacto")
    c1, c2 = st.columns(2)
    with c1:
        ciudad = st.text_input("Ciudad").upper()
        barrio = st.text_input("Barrio").upper()
        telefono = st.text_input("Teléfono")
    with c2:
        direccion = st.text_input("Dirección").upper()
        ocupacion = st.text_input("Ocupación").upper()
        
    st.markdown("---")
    
    # Acción de búsqueda
    buscar_puesto = st.form_submit_button("🔍 Validar y Buscar Puesto de Votación")
    
    if buscar_puesto:
        if not validar_cedula_real(cedula):
            st.error("❌ El número de cédula debe tener entre 7 y 10 dígitos.")
        elif not (barrio and ciudad):
            st.warning("⚠️ Ingrese Barrio y Ciudad para buscar el puesto.")
        else:
            with st.spinner("🤖 Consultando puesto oficial con IA..."):
                puesto = consultar_puesto_ia(cedula, barrio, ciudad)
                st.session_state.lugar_detectado = puesto
                st.success(f"📍 Puesto encontrado: {puesto}")

    # Lugar de votación (se llena solo)
    lugar_final = st.text_input("Lugar de Votación Asignado", value=st.session_state.lugar_detectado, disabled=True)
    
    # Guardar
    if st.form_submit_button("✅ Finalizar Registro"):
        if not st.session_state.lugar_detectado:
            st.error("Primero debe buscar el puesto de votación con el botón de la lupa.")
        elif not (nombre and cedula):
            st.error("El nombre y la cédula son obligatorios.")
        else:
            data = {
                "nombre": nombre, "cedula": cedula, "telefono": telefono,
                "ocupacion": ocupacion, "direccion": direccion, "barrio": barrio,
                "ciudad": ciudad, "lugar_votacion": st.session_state.lugar_detectado
            }
            if save_and_learn(data):
                st.success("✅ ¡Registro exitoso!")
                st.session_state.lugar_detectado = ""
                time.sleep(2)
                st.rerun()

st.sidebar.markdown(f"### 👤 {st.session_state.user_name.capitalize()}")
if st.sidebar.button("Salir"):
    st.session_state.logged_in = False
    st.rerun()
