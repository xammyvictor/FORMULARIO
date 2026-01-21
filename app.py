import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO
import plotly.express as px

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"

st.set_page_config(
    page_title="Sistema Maria Irma - Gestión Ciudadana",
    page_icon="🗳️",
    layout="wide" # Cambiado a wide para mejor visualización de tablas y mapas
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #333333 !important; }
    header, [data-testid="stHeader"] { background-color: #FFFFFF !important; }
    [data-testid="stHeader"] svg, [data-testid="stSidebarCollapsedControl"] svg { fill: #333333 !important; }
    h1, h2, h3 { color: #D81B60 !important; text-align: center; }
    .stButton>button { width: 100%; background-color: #E91E63 !important; color: white !important; border-radius: 8px; }
    [data-testid="stSidebar"] { background-color: #FCE4EC !important; }
    .guest-banner { padding: 15px; background-color: #F8BBD0; color: #880E4F !important; border-radius: 8px; text-align: center; border: 1px solid #F48FB1; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def get_all_data(file_name="Base_Datos_Ciudadanos"):
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open(file_name)
        data = sh.sheet1.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def save_to_drive(data_dict, file_name="Base_Datos_Ciudadanos"):
    client = get_google_sheet_client()
    if not client: return False
    try:
        try:
            sh = client.open(file_name)
            worksheet = sh.sheet1
        except gspread.SpreadsheetNotFound:
            sh = client.create(file_name)
            if "admin_email" in st.secrets:
                sh.share(st.secrets["admin_email"], perm_type='user', role='writer')
            worksheet = sh.sheet1
            headers = ["Fecha Registro", "Registrado Por", "Nombre Completo", "Cédula", "Teléfono", "Ocupación", "Dirección", "Barrio", "Ciudad"]
            worksheet.append_row(headers)

        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_actual = st.session_state.get("user_name", "Desconocido")
        row = [timestamp, usuario_actual, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
               data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], data_dict["ciudad"]]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- LÓGICA DE SESIÓN ---
def check_session():
    if "query_params_checked" not in st.session_state:
        try:
            params = st.query_params
            if "ref" in params:
                st.session_state.logged_in = True
                st.session_state.user_name = params["ref"]
                st.session_state.is_guest = True
        except: pass
        st.session_state.query_params_checked = True

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.is_guest = False

    if not st.session_state.logged_in:
        st.title("🔐 Acceso al Sistema")
        with st.form("login_form"):
            user = st.text_input("Usuario").lower().strip()
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                credenciales = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "arturo": "1234"}
                if user in credenciales and credenciales[user] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

# --- NAVEGACIÓN ---
if check_session():
    usuario = st.session_state.user_name
    
    # Menú Lateral
    st.sidebar.title(f"Bienvenido, {usuario.capitalize()}")
    opcion = st.sidebar.radio("Ir a:", ["📝 Registro Nuevo", "🔍 Búsqueda Rápida", "📊 Estadísticas y Mapa"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

    # --- SECCIÓN 1: REGISTRO ---
    if opcion == "📝 Registro Nuevo":
        st.title("🗳️ Formulario de Registro")
        if st.session_state.get("is_guest"):
            st.markdown(f'<div class="guest-banner">Modo Invitado: Registrando para <b>{usuario}</b></div>', unsafe_allow_html=True)

        with st.form("registro_form"):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre Completo")
            cedula = col1.text_input("Cédula")
            telef = col1.text_input("Teléfono")
            ocupa = col1.text_input("Ocupación")
            direc = col2.text_input("Dirección")
            barrio = col2.text_input("Barrio")
            ciudad = col2.text_input("Ciudad", value="Buga") # Ciudad por defecto
            
            if st.form_submit_button("Enviar Registro"):
                if all([nombre, cedula, telef, ciudad]):
                    data = {"nombre": nombre.upper(), "cedula": cedula, "telefono": telef, "ocupacion": ocupa.upper(), 
                            "direccion": direc.upper(), "barrio": barrio.upper(), "ciudad": ciudad.upper()}
                    if save_to_drive(data):
                        st.success("✅ ¡Guardado exitosamente!")
                        time.sleep(1)
                        st.rerun()
                else: st.error("⚠️ Nombre, Cédula, Teléfono y Ciudad son obligatorios.")

    # --- SECCIÓN 2: BÚSQUEDA ---
    elif opcion == "🔍 Búsqueda Rápida":
        st.title("🔍 Consulta de Ciudadanos")
        df = get_all_data()
        if not df.empty:
            busqueda = st.text_input("Buscar por Nombre o Cédula:").upper()
            if busqueda:
                # Convertir todo a string para búsqueda segura
                df_str = df.astype(str)
                resultado = df[df_str.apply(lambda row: busqueda in row.values, axis=1)]
                if not resultado.empty:
                    st.dataframe(resultado, use_container_width=True)
                else: st.warning("No se encontraron coincidencias.")
            else:
                st.write("Últimos registros:")
                st.dataframe(df.tail(10), use_container_width=True)
        else: st.info("No hay datos registrados aún.")

    # --- SECCIÓN 3: ESTADÍSTICAS Y MAPA ---
    elif opcion == "📊 Estadísticas y Mapa":
        st.title("📊 Análisis de Datos")
        df = get_all_data()
        
        if not df.empty:
            # Métricas rápidas
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Registrados", len(df))
            c2.metric("Ciudades", df['Ciudad'].nunique())
            c3.metric("Líder más activo", df['Registrado Por'].mode()[0])

            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("Distribución por Ciudad")
                fig_city = px.pie(df, names='Ciudad', hole=0.4, color_discrete_sequence=px.colors.sequential.RdPu)
                st.plotly_chart(fig_city, use_container_width=True)

            with col_right:
                st.subheader("Registros por Usuario")
                fig_user = px.bar(df['Registrado Por'].value_counts(), labels={'value':'Cantidad', 'index':'Usuario'}, color_discrete_sequence=['#D81B60'])
                st.plotly_chart(fig_user, use_container_width=True)

            # --- MAPA DE CALOR (SIMULADO POR CIUDAD) ---
            st.subheader("📍 Mapa de Concentración por Ciudad")
            
            # Diccionario de coordenadas básicas de Colombia (puedes ampliarlo)
            coords = {
                'BUGA': [3.9009, -76.3008], 'CALI': [3.4516, -76.5320], 'BOGOTA': [4.7110, -74.0721],
                'MEDELLIN': [6.2442, -75.5812], 'PALMIRA': [3.5394, -76.3036], 'TULUA': [4.0847, -76.1954],
                'CARTAGO': [4.7464, -75.9117], 'YUMBO': [3.5411, -76.4911]
            }

            # Preparar datos para el mapa
            map_data = df['Ciudad'].value_counts().reset_index()
            map_data.columns = ['Ciudad', 'Cantidad']
            map_data['lat'] = map_data['Ciudad'].apply(lambda x: coords.get(x.strip().upper(), [3.9, -76.3])[0])
            map_data['lon'] = map_data['Ciudad'].apply(lambda x: coords.get(x.strip().upper(), [3.9, -76.3])[1])

            # Mostrar Mapa
            fig_map = px.scatter_mapbox(map_data, lat="lat", lon="lon", size="Cantidad", color="Cantidad",
                                      color_continuous_scale=px.colors.sequential.RdPu, size_max=40, zoom=6,
                                      mapbox_style="carto-positron", title="Densidad de Registros")
            st.plotly_chart(fig_map, use_container_width=True)

        else: st.info("No hay datos para mostrar estadísticas.")
