import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

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
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
# IMPORTANTE: Estas URLs deben estar limpias, sin corchetes extraños
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_sheet_client():
    try:
        # Cargamos las credenciales desde los secretos de Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error de autenticación: {e}")
        return None

def save_to_drive(data_dict, file_name="Base_Datos_Ciudadanos"):
    client = get_google_sheet_client()
    if not client: return False

    try:
        try:
            sh = client.open(file_name)
            worksheet = sh.sheet1
        except gspread.SpreadsheetNotFound:
            st.info(f"Creando archivo '{file_name}' en Drive...")
            sh = client.create(file_name)
            sh.share(st.secrets["admin_email"], perm_type='user', role='writer')
            worksheet = sh.sheet1
            headers = ["Fecha Registro", "Nombre Completo", "Cédula", "Teléfono", 
                       "Ocupación", "Dirección", "Barrio", "Ciudad"]
            worksheet.append_row(headers)

        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], data_dict["ciudad"]
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- INTERFAZ DE USUARIO ---
st.title("🗳️ Registro de Datos Ciudadanos")
st.markdown("---")
st.write("Complete el formulario para el registro en la base de datos centralizada.")

with st.form("registro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre Completo")
        cedula = st.text_input("Cédula de Ciudadanía")
        telefono = st.text_input("Teléfono")
        ocupacion = st.text_input("Ocupación")
    with col2:
        direccion = st.text_input("Dirección")
        barrio = st.text_input("Barrio")
        ciudad = st.text_input("Ciudad")
    
    st.markdown("### Confirmación")
    submitted = st.form_submit_button("Enviar Registro")

    if submitted:
        if not all([nombre, cedula, telefono, ocupacion, direccion, barrio, ciudad]):
            st.warning("⚠️ Por favor complete todos los campos.")
        else:
            data = {
                "nombre": nombre, "cedula": cedula, "telefono": telefono,
                "ocupacion": ocupacion, "direccion": direccion, "barrio": barrio, "ciudad": ciudad
            }
            with st.spinner('Guardando en Google Drive...'):
                if save_to_drive(data):
                    st.success("✅ ¡Datos guardados exitosamente!")
                    time.sleep(2)
                    st.rerun()
