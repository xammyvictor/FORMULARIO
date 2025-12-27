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

# Estilos CSS personalizados para dar una apariencia institucional
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1 {
        color: #0f3460;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
        background-color: #0f3460;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
# Definimos los alcances (scopes) necesarios para la API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_sheet_client():
    """
    Autentica y retorna el cliente de gspread usando st.secrets.
    Maneja la conexión segura sin exponer credenciales en el código.
    """
    try:
        # Cargamos las credenciales desde los secretos de Streamlit (.streamlit/secrets.toml)
        # Esto es vital para la seguridad en repositorios públicos.
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error de autenticación con Google: {e}")
        return None

def save_to_drive(data_dict, file_name="Base_Datos_Ciudadanos"):
    """
    Guarda los datos en Google Sheets. Si el archivo no existe, lo crea.
    """
    client = get_google_sheet_client()
    if not client:
        return False

    try:
        # Intentar abrir la hoja de cálculo existente
        try:
            sh = client.open(file_name)
            worksheet = sh.sheet1
        except gspread.SpreadsheetNotFound:
            # Si no existe, crear una nueva
            st.info(f"El archivo '{file_name}' no existía. Creando uno nuevo en Drive...")
            sh = client.create(file_name)
            sh.share(st.secrets["admin_email"], perm_type='user', role='writer') # Compartir con el admin
            worksheet = sh.sheet1
            # Crear encabezados
            headers = ["Fecha Registro", "Nombre Completo", "Cédula", "Teléfono", 
                       "Ocupación", "Dirección", "Barrio", "Ciudad"]
            worksheet.append_row(headers)

        # Preparar la fila de datos
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            data_dict["nombre"],
            data_dict["cedula"],
            data_dict["telefono"],
            data_dict["ocupacion"],
            data_dict["direccion"],
            data_dict["barrio"],
            data_dict["ciudad"]
        ]

        # Agregar la fila
        worksheet.append_row(row)
        return True

    except Exception as e:
        st.error(f"Error al guardar los datos en Drive: {e}")
        return False

# --- INTERFAZ DE USUARIO ---

st.title("🗳️ Registro de Datos Ciudadanos")
st.markdown("---")
st.write("Complete el siguiente formulario para el registro en la base de datos centralizada.")

# Formulario de entrada
with st.form("registro_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre Completo")
        cedula = st.text_input("Cédula de Ciudadanía")
        telefono = st.text_input("Teléfono de Contacto")
        ocupacion = st.text_input("Ocupación")
        
    with col2:
        direccion = st.text_input("Dirección de Residencia")
        barrio = st.text_input("Barrio")
        ciudad = st.text_input("Ciudad")
    
    st.markdown("###Confirmación")
    submitted = st.form_submit_button("Enviar Registro")

    if submitted:
        # 1. Validación de campos vacíos
        if not all([nombre, cedula, telefono, ocupacion, direccion, barrio, ciudad]):
            st.warning("⚠️ Por favor complete todos los campos antes de enviar.")
        else:
            # 2. Preparación de datos
            data = {
                "nombre": nombre,
                "cedula": cedula,
                "telefono": telefono,
                "ocupacion": ocupacion,
                "direccion": direccion,
                "barrio": barrio,
                "ciudad": ciudad
            }
            
            # 3. Guardado con indicador de carga
            with st.spinner('Conectando con Google Drive y guardando datos...'):
                success = save_to_drive(data)
            
            # 4. Feedback al usuario
            if success:
                st.success("✅ ¡Datos guardados exitosamente en la nube!")
                time.sleep(2) # Pausa breve para que el usuario lea
                st.rerun() # Recargar para limpiar formulario visualmente
            else:
                st.error("❌ Hubo un problema al conectar con la base de datos.")

# Footer institucional
st.markdown("---")
st.caption("Sistema de Gestión de Información | Sector Público & Transparencia Digital")
