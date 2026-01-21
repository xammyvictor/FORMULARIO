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
    layout="wide"
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #333333 !important; }
    header, [data-testid="stHeader"] { background-color: #FFFFFF !important; }
    h1, h2, h3 { color: #D81B60 !important; text-align: center; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stButton>button { width: 100%; background-color: #E91E63 !important; color: white !important; border-radius: 8px; font-weight: bold; height: 3em; }
    .stButton>button:hover { background-color: #C2185B !important; border-color: #C2185B !important; }
    [data-testid="stSidebar"] { background-color: #FCE4EC !important; }
    .guest-banner { padding: 15px; background-color: #F8BBD0; color: #880E4F !important; border-radius: 8px; text-align: center; border: 1px solid #F48FB1; margin-bottom: 20px;}
    /* Ajuste para que los labels se vean negros */
    label { color: #333333 !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Error: Credenciales 'gcp_service_account' no encontradas en Secrets.")
            return None
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error de conexión con Google: {e}")
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

# --- INICIALIZACIÓN DE ESTADO DEL FORMULARIO ---
campos_form = ["nombre", "cedula", "telefono", "ocupacion", "direccion", "barrio", "ciudad"]
for campo in campos_form:
    if f"val_{campo}" not in st.session_state:
        st.session_state[f"val_{campo}"] = "" if campo != "ciudad" else "BUGA"

# --- FLUJO PRINCIPAL ---
if check_session():
    usuario = st.session_state.user_name
    
    # Barra Lateral
    st.sidebar.markdown(f"## Hola, **{usuario.capitalize()}**")
    opcion = st.sidebar.radio("Navegación:", ["📝 Registro Nuevo", "🔍 Búsqueda Rápida", "📊 Estadísticas y Mapa"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- SECCIÓN 1: REGISTRO ---
    if opcion == "📝 Registro Nuevo":
        st.title("🗳️ Nuevo Registro de Ciudadano")
        if st.session_state.get("is_guest"):
            st.markdown(f'<div class="guest-banner">👋 Registrando para el equipo de: <b>{usuario.capitalize()}</b></div>', unsafe_allow_html=True)

        # Formulario con clear_on_submit=False para controlar el borrado manualmente
        with st.form("registro_form", clear_on_submit=False):
            st.subheader("Información Personal")
            col1, col2 = st.columns(2)
            
            with col1:
                in_nombre = st.text_input("Nombre Completo", value=st.session_state.val_nombre)
                in_cedula = st.text_input("Número de Cédula", value=st.session_state.val_cedula, help="Solo números")
                in_telefono = st.text_input("Número de Teléfono", value=st.session_state.val_telefono, help="Solo números")
            
            with col2:
                in_ocupacion = st.text_input("Ocupación", value=st.session_state.val_ocupacion)
                in_direccion = st.text_input("Dirección", value=st.session_state.val_direccion)
                in_barrio = st.text_input("Barrio", value=st.session_state.val_barrio)
            
            in_ciudad = st.text_input("Ciudad", value=st.session_state.val_ciudad)
            
            st.markdown("---")
            enviar = st.form_submit_button("✅ Guardar Registro")

            if enviar:
                # 1. Guardar temporalmente en session_state lo que el usuario escribió
                st.session_state.val_nombre = in_nombre
                st.session_state.val_cedula = in_cedula
                st.session_state.val_telefono = in_telefono
                st.session_state.val_ocupacion = in_ocupacion
                st.session_state.val_direccion = in_direccion
                st.session_state.val_barrio = in_barrio
                st.session_state.val_ciudad = in_ciudad

                # 2. Validaciones
                errores = []
                
                # Campos vacíos
                if not all([in_nombre.strip(), in_cedula.strip(), in_telefono.strip(), in_ocupacion.strip(), 
                            in_direccion.strip(), in_barrio.strip(), in_ciudad.strip()]):
                    errores.append("⚠️ Todos los campos son obligatorios.")
                
                # Solo números en Cédula y Teléfono
                if in_cedula.strip() and not in_cedula.strip().isdigit():
                    errores.append("❌ La Cédula debe contener solo números.")
                
                if in_telefono.strip() and not in_telefono.strip().isdigit():
                    errores.append("❌ El Teléfono debe contener solo números.")

                if errores:
                    for error in errores:
                        st.error(error)
                else:
                    # 3. Procesar Envío
                    data = {
                        "nombre": in_nombre.strip().upper(),
                        "cedula": in_cedula.strip(),
                        "telefono": in_telefono.strip(),
                        "ocupacion": in_ocupacion.strip().upper(),
                        "direccion": in_direccion.strip().upper(),
                        "barrio": in_barrio.strip().upper(),
                        "ciudad": in_ciudad.strip().upper()
                    }
                    
                    with st.spinner("Guardando en la base de datos..."):
                        if save_to_drive(data):
                            st.success(f"✅ ¡Registro de {in_nombre.upper()} guardado exitosamente!")
                            
                            # 4. Limpiar el formulario solo en éxito
                            for campo in campos_form:
                                st.session_state[f"val_{campo}"] = "" if campo != "ciudad" else "BUGA"
                            
                            time.sleep(2)
                            st.rerun()

    # --- SECCIÓN 2: BÚSQUEDA ---
    elif opcion == "🔍 Búsqueda Rápida":
        st.title("🔍 Consulta de Ciudadanos")
        df = get_all_data()
        if not df.empty:
            busqueda = st.text_input("Buscar por Nombre o Cédula:").upper()
            if busqueda:
                mask = df.astype(str).apply(lambda row: row.str.contains(busqueda).any(), axis=1)
                resultado = df[mask]
                if not resultado.empty:
                    st.dataframe(resultado, use_container_width=True)
                else: st.warning("No se encontraron coincidencias.")
            else:
                st.info("Mostrando los registros más recientes:")
                st.dataframe(df.tail(15), use_container_width=True)
        else: st.warning("Base de datos vacía.")

    # --- SECCIÓN 3: ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas y Mapa":
        st.title("📊 Análisis de Registros")
        df = get_all_data()
        
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Registrados", len(df))
            m2.metric("Ciudades Cubiertas", df['Ciudad'].nunique())
            m3.metric("Último Registro", df.iloc[-1]['Nombre Completo'] if not df.empty else "N/A")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Concentración por Ciudad")
                fig_pie = px.pie(df, names='Ciudad', color_discrete_sequence=px.colors.sequential.RdPu)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with c2:
                st.subheader("Desempeño de Líderes")
                fig_bar = px.bar(df['Registrado Por'].value_counts(), color_discrete_sequence=['#D81B60'])
                st.plotly_chart(fig_bar, use_container_width=True)

            # Mapa
            st.subheader("📍 Cobertura Geográfica")
            coords = {'BUGA': [3.9009, -76.3008], 'CALI': [3.4516, -76.5320], 'PALMIRA': [3.5394, -76.3036], 'TULUA': [4.0847, -76.1954]}
            map_df = df['Ciudad'].str.upper().value_counts().reset_index()
            map_df.columns = ['Ciudad', 'Cantidad']
            map_df['lat'] = map_df['Ciudad'].apply(lambda x: coords.get(x.strip(), [3.9, -76.3])[0])
            map_df['lon'] = map_df['Ciudad'].apply(lambda x: coords.get(x.strip(), [3.9, -76.3])[1])
            
            fig_map = px.scatter_mapbox(map_df, lat="lat", lon="lon", size="Cantidad", color="Cantidad",
                                      color_continuous_scale="RdPu", zoom=7, mapbox_style="carto-positron")
            st.plotly_chart(fig_map, use_container_width=True)
