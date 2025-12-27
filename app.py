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

# --- SISTEMA DE LOGIN Y CONTROL DE SESIÓN ---
def check_session():
    # 1. Revisar si viene referido por QR (Invitado)
    try:
        query_params = st.query_params
    except:
        query_params = st.experimental_get_query_params()
        
    ref_user = query_params.get("ref")
    
    # Si hay un referido en la URL, iniciamos sesión como invitado automáticamente
    if ref_user:
        # Si es una lista (versiones viejas), sacamos el primer elemento
        if isinstance(ref_user, list):
            ref_user = ref_user[0]
            
        st.session_state.logged_in = True
        st.session_state.user_name = ref_user
        st.session_state.is_guest = True # Marcamos que es invitado
        return True

    # 2. Si no es invitado, revisamos login normal
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.is_guest = False
    
    if st.session_state.logged_in:
        return True

    # 3. Mostrar Pantalla de Login
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
                st.session_state.is_guest = False # Es admin/usuario real
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    return False

# --- FLUJO PRINCIPAL DE LA APP ---

# 1. Verificar Login (o Referido QR)
if not check_session():
    st.stop()

# 2. Barra lateral (Diferente para Admin vs Invitado)
usuario = st.session_state.user_name

if st.session_state.get("is_guest", False):
    # Vista para el ASISTENTE (Invitado)
    st.sidebar.info(f"📋 Formulario de Registro\n\nResponsable: **{usuario.capitalize()}**")
else:
    # Vista para el USUARIO REGISTRADO (Admin)
    st.sidebar.markdown(f"### 👤 Usuario: **{usuario.capitalize()}**")
    
    # GENERADOR DE QR CON BOTÓN
    with st.sidebar.expander("📱 Generar QR para Asistentes", expanded=True):
        st.write("Crea un QR para que otros llenen el formulario bajo tu nombre.")
        
        # Campo de texto para la URL (por defecto usa BASE_URL)
        url_input = st.text_input("URL Pública de la App:", value=BASE_URL)
        
        # Botón para generar el QR
        if st.button("Generar QR"):
            # Limpiamos la URL
            clean_url = url_input.strip().rstrip("/")
            link_registro = f"{clean_url}?ref={usuario}"
            
            # Generar imagen QR
            try:
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(link_registro)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Convertir a bytes para mostrar
                buf = BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.image(byte_im, caption=f"Invitación de {usuario}", use_column_width=True)
                st.success("¡QR generado exitosamente!")
            except Exception as e:
                st.error(f"Error generando QR: {e}")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.is_guest = False
        # Limpiar query params al salir
        try:
            st.query_params.clear()
        except:
            st.experimental_set_query_params()
        st.rerun()

# 3. Formulario Principal
st.title("🗳️ Registro de Datos Ciudadanos")
if st.session_state.get("is_guest", False):
    st.markdown(f"""
    <div style="padding:10px; background-color:#d1ecf1; color:#0c5460; border-radius:5px; margin-bottom:10px;">
        👋 <b>Modo Invitado:</b> Estás registrando datos para: <b>{usuario.capitalize()}</b>
    </div>
    """, unsafe_allow_html=True)

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
