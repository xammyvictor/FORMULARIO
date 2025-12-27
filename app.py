import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO

# --- CONFIGURACIÓN GENERAL ---
# URL de tu aplicación (IMPORTANTE: Sin corchetes ni paréntesis extraños)
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"

# Configuración de la página
st.set_page_config(
    page_title="Formulario de Registro Ciudadano",
    page_icon="🗳️",
    layout="centered"
)

# --- ESTILOS VISUALES (BLANCO Y ROSADO) ---
# Se ha actualizado la paleta de colores:
# Fondo: Blanco (#FFFFFF)
# Color Principal (Botones/Títulos): Rosado (#E91E63 y variantes)
# Sidebar: Rosado muy pálido para diferenciar (#FCE4EC)

st.markdown("""
    <style>
    /* Fondo principal blanco */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Color de Títulos y Encabezados */
    h1, h2, h3 { 
        color: #D81B60 !important; 
        text-align: center; 
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Estilo de los Botones (Rosado) */
    .stButton>button { 
        width: 100%; 
        background-color: #E91E63; 
        color: white; 
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    /* Efecto Hover en Botones (Oscurecer un poco al pasar el mouse) */
    .stButton>button:hover {
        background-color: #C2185B;
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Personalización del Sidebar (Fondo rosado muy suave) */
    [data-testid="stSidebar"] {
        background-color: #FCE4EC;
    }
    
    /* Mensajes de éxito (Verde suave para mantener semántica, pero con borde rosado opcional) */
    .stSuccess { 
        background-color: #d4edda; 
        color: #155724; 
        padding: 10px; 
        border-radius: 5px;
        border-left: 5px solid #E91E63;
    }
    
    /* Inputs de texto (Borde rosado al enfocar) */
    input:focus {
        border-color: #E91E63 !important;
        box-shadow: 0 0 0 1px #E91E63 !important;
    }
    
    /* Estilo para el modo invitado */
    .guest-banner {
        padding: 15px; 
        background-color: #F8BBD0; /* Rosado pastel */
        color: #880E4F; /* Texto vino tinto */
        border-radius: 8px; 
        margin-bottom: 20px;
        text-align: center;
        border: 1px solid #F48FB1;
    }
    </style>
    """, unsafe_allow_html=True)



# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
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
            # Asegúrate de que 'admin_email' exista en st.secrets o maneja el error
            if "admin_email" in st.secrets:
                sh.share(st.secrets["admin_email"], perm_type='user', role='writer')
            worksheet = sh.sheet1
            # Encabezados
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
        # Fallback para versiones antiguas de Streamlit
        query_params = st.experimental_get_query_params()
        
    ref_user = query_params.get("ref")
    
    # Si hay un referido en la URL, iniciamos sesión como invitado automáticamente
    if ref_user:
        # Si es una lista (dependiendo de la versión de streamlit), sacamos el primer elemento
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
    st.markdown("<p style='text-align: center; color: #666;'>Ingrese sus credenciales para gestionar el registro.</p>", unsafe_allow_html=True)

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
    st.sidebar.info(f"📋 Registro Activo\n\nResponsable: **{usuario.capitalize()}**")
else:
    # Vista para el USUARIO REGISTRADO (Admin)
    st.sidebar.markdown(f"### 👤 Usuario: **{usuario.capitalize()}**")
    
    # GENERADOR DE QR CON BOTÓN
    with st.sidebar.expander("📱 Generar QR", expanded=True):
        st.write("QR para asistentes:")
        
        # Campo de texto para la URL (por defecto usa BASE_URL)
        url_input = st.text_input("URL App:", value=BASE_URL)
        
        # Botón para generar el QR
        if st.button("Generar Código QR"):
            # Limpiamos la URL
            clean_url = url_input.strip().rstrip("/")
            link_registro = f"{clean_url}?ref={usuario}"
            
            # Generar imagen QR
            try:
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(link_registro)
                qr.make(fit=True)
                img = qr.make_image(fill_color="#E91E63", back_color="white") # QR Rosado
                
                # Convertir a bytes para mostrar
                buf = BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.image(byte_im, caption=f"QR de {usuario}", use_column_width=True)
                st.success("¡QR listo!")
            except Exception as e:
                st.error(f"Error QR: {e}")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.is_guest = False
        # Limpiar query params al salir
        try:
            st.query_params.clear()
        except:
            # Fallback para versiones antiguas
            st.experimental_set_query_params()
        st.rerun()

# 3. Formulario Principal
st.title("🗳️ Registro Ciudadano")

if st.session_state.get("is_guest", False):
    st.markdown(f"""
    <div class="guest-banner">
        👋 <b>Modo Invitado:</b> Estás registrando datos para: <b>{usuario.capitalize()}</b>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.write("Complete la información del ciudadano a continuación.")

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
