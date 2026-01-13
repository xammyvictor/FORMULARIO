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
# La clave se maneja internamente en el entorno de ejecución
apiKey = "" 

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
    .error-box { padding: 20px; background-color: #ffebee; border: 1px solid #c62828; border-radius: 10px; color: #c62828; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE IA Y BÚSQUEDA ---

def consultar_puesto_ia(cedula, barrio, ciudad):
    """
    Usa la API de Gemini para identificar el puesto de votación.
    Implementa reintentos con backoff exponencial según requerimiento técnico.
    """
    system_prompt = "Eres un asistente experto en el sistema electoral colombiano. Identifica el puesto de votación oficial para el barrio y ciudad indicados. Responde BREVE con Nombre y Dirección."
    user_query = f"¿Cuál es el puesto de votación para el barrio {barrio} en {ciudad}, Colombia?"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {
        "contents": [{ "parts": [{ "text": user_query }] }],
        "systemInstruction": { "parts": [{ "text": system_prompt }] },
        "tools": [{ "google_search": {} }]
    }

    # Reintentos: 1s, 2s, 4s, 8s, 16s
    for i in range(5):
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                # Extraer texto según estructura de la API
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return text.strip() if text else "Puesto no localizado"
            time.sleep(2**i) 
        except:
            time.sleep(2**i)
            
    return "Error de conexión con la IA. Por favor ingrese el puesto manualmente."

def validar_cedula_real(cedula_str):
    return bool(re.match(r'^\d{7,10}$', cedula_str))

# --- CONEXIÓN A DRIVE ---
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("⚠️ Falta la configuración 'gcp_service_account' en los Secretos de Streamlit.")
            return None
        
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=[
            "https://www.googleapis.com/auth/spreadsheets", 
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        return None

def save_and_learn(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        # Intenta abrir el archivo. Asegúrate de que el nombre sea exacto.
        try:
            sh = client.open("Base_Datos_Ciudadanos")
        except gspread.SpreadsheetNotFound:
            st.error("❌ No se encontró el archivo 'Base_Datos_Ciudadanos' en tu Google Drive. Asegúrate de haberlo compartido con el correo de la cuenta de servicio.")
            return False
            
        ws_reg = sh.sheet1
        row = [
            pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.get("user_name", "invitado"),
            data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"],
            data_dict["ciudad"], data_dict["lugar_votacion"]
        ]
        ws_reg.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        return False

# --- SESIÓN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso al Sistema")
    with st.form("login_ui"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            if p == "1234":
                st.session_state.logged_in = True
                st.session_state.user_name = u
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- FORMULARIO PRINCIPAL ---
st.title("🗳️ Maria Irma - Registro Ciudadano")

if "lugar_detectado" not in st.session_state: st.session_state.lugar_detectado = ""

with st.form("main_form"):
    st.markdown("### 1. Datos Personales")
    c1, c2 = st.columns(2)
    with c1:
        cedula = st.text_input("Número de Cédula")
        nombre = st.text_input("Nombre Completo").upper()
        telefono = st.text_input("Teléfono")
    with c2:
        ocupacion = st.text_input("Ocupación").upper()
        ciudad = st.text_input("Ciudad").upper()
        barrio = st.text_input("Barrio").upper()
    
    direccion = st.text_input("Dirección de Residencia").upper()

    st.markdown("---")
    st.markdown("### 2. Puesto de Votación")
    
    btn_buscar = st.form_submit_button("🔍 BUSCAR PUESTO AUTOMÁTICAMENTE")
    
    if btn_buscar:
        if not validar_cedula_real(cedula):
            st.error("Cédula inválida (debe tener entre 7 y 10 números).")
        elif not (barrio and ciudad):
            st.warning("Ingrese Barrio y Ciudad para localizar el puesto.")
        else:
            with st.spinner("🤖 Consultando ubicación oficial..."):
                puesto = consultar_puesto_ia(cedula, barrio, ciudad)
                st.session_state.lugar_detectado = puesto
                st.success(f"📍 Puesto Sugerido: {puesto}")

    lugar_final = st.text_input("Puesto Asignado", value=st.session_state.lugar_detectado, disabled=True)
    
    st.markdown("---")
    if st.form_submit_button("✅ FINALIZAR Y GUARDAR REGISTRO"):
        if not st.session_state.lugar_detectado:
            st.error("Primero debe buscar el puesto con el botón de la lupa.")
        elif not (nombre and cedula):
            st.error("Nombre y Cédula son obligatorios.")
        else:
            data = {
                "nombre": nombre, "cedula": cedula, "telefono": telefono,
                "ocupacion": ocupacion, "direccion": direccion, "barrio": barrio,
                "ciudad": ciudad, "lugar_votacion": st.session_state.lugar_detectado
            }
            if save_and_learn(data):
                st.success("✅ ¡Registro Guardado Exitosamente!")
                st.session_state.lugar_detectado = ""
                time.sleep(2)
                st.rerun()

# SIDEBAR
with st.sidebar:
    st.write(f"👤 Usuario: {st.session_state.user_name}")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()
