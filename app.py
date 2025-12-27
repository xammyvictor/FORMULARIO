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
# ASÍ DEBE QUEDAR (Limpio):
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
            # Ahora incluimos QUIÉN registró el dato
            headers = ["Fecha Registro", "Registrado Por", "Nombre Completo", "Cédula", "Teléfono", 
                       "Ocupación", "Dirección", "Barrio", "Ciudad"]
            worksheet.append_row(headers)

        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        # Obtenemos el usuario actual de la sesión
        usuario_actual = st.session_state.get("user_name", "Desconocido")
        
        row = [
            timestamp, usuario_actual, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
            data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], data_dict["ciudad"]
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- SISTEMA DE LOGIN ---
def login():
    # Inicializar estado de login si no existe
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        return True

    st.title("🔐 Acceso al Sistema")
    st.markdown("Por favor ingrese sus credenciales.")

    with st.form("login_form"):
        user = st.text_input("Usuario").lower().strip()
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")

        if submitted:
            # USUARIOS CONFIGURADOS
            credenciales = {
                "fabian": "1234",
                "xammy": "1234",
                "brayan": "1234"
            }
            
            if user in credenciales and credenciales[user] == password:
                st.session_state.logged_in = True
                st.session_state.user_name = user
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    return False

# --- FLUJO PRINCIPAL DE LA APP ---

# 1. Verificar Login
if not login():
    st.stop()

# 2. Barra lateral con info de usuario
st.sidebar.markdown(f"### 👤 Usuario: **{st.session_state.user_name.capitalize()}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

# 3. Formulario Principal (Solo visible si está logueado)
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
