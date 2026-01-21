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
    label { color: #333333 !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Error: Credenciales 'gcp_service_account' no encontradas.")
            return None
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
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
        return df
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
            headers = ["Fecha Registro", "Registrado Por", "Nombre", "Cédula", "Teléfono", "Ocupación", "Dirección", "Barrio", "Ciudad", "Puesto votacion"]
            worksheet.append_row(headers)

        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_actual = st.session_state.get("user_name", "Desconocido")
        
        row = [
            timestamp, 
            usuario_actual, 
            data_dict["nombre"], 
            data_dict["cedula"], 
            data_dict["telefono"],
            data_dict["ocupacion"], 
            data_dict["direccion"], 
            data_dict["barrio"], 
            data_dict["ciudad"],
            data_dict.get("puesto", "")
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- LÓGICA DE SESIÓN ---
def check_session():
    if "query_params_checked" not in st.session_state:
        try:
            try:
                params = st.query_params
            except:
                params = st.experimental_get_query_params()
                
            if "ref" in params:
                ref_user = params["ref"]
                if isinstance(ref_user, list): ref_user = ref_user[0]
                st.session_state.logged_in = True
                st.session_state.user_name = ref_user
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
                credenciales = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "DiegoMonta": "1234"}
                if user in credenciales and credenciales[user] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
        return False
    return True

# --- INICIALIZACIÓN DE ESTADO ---
campos_form = ["nombre", "cedula", "telefono", "ocupacion", "direccion", "barrio", "ciudad", "puesto"]
for campo in campos_form:
    if f"val_{campo}" not in st.session_state:
        st.session_state[f"val_{campo}"] = "" if campo != "ciudad" else "BUGA"

# --- FLUJO PRINCIPAL ---
if check_session():
    usuario = st.session_state.user_name
    
    # BARRA LATERAL
    st.sidebar.markdown(f"### 👤 Usuario: **{usuario.capitalize()}**")
    
    # --- RESTRICCIÓN DE ACCESO A MÓDULOS DE DATOS ---
    # Solo estos usuarios pueden ver estadísticas y búsqueda rápida
    USUARIOS_CON_ACCESO_TOTAL = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_CON_ACCESO_TOTAL and not st.session_state.get("is_guest", False)

    if es_admin:
        opciones_menu = ["📝 Registro Nuevo", "🔍 Búsqueda Rápida", "📊 Estadísticas"]
    else:
        opciones_menu = ["📝 Registro Nuevo"]
        if not st.session_state.get("is_guest", False):
            st.sidebar.warning("Acceso limitado: Registro habilitado.")

    opcion = st.sidebar.radio("Navegación:", opciones_menu)
    
    # GENERADOR DE QR (Habilitado para TODOS los usuarios con cuenta, excepto invitados)
    if not st.session_state.get("is_guest", False):
        with st.sidebar.expander("📱 Generar QR", expanded=False):
            st.write("QR para que otros se registren bajo tu nombre:")
            url_input = st.text_input("URL Base:", value=BASE_URL)
            if st.button("Generar Código QR"):
                clean_url = url_input.strip().rstrip("/")
                link_registro = f"{clean_url}?ref={usuario}"
                try:
                    qr = qrcode.QRCode(box_size=10, border=4)
                    qr.add_data(link_registro)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="#E91E63", back_color="white")
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption=f"QR de {usuario.capitalize()}", use_column_width=True)
                    st.success("¡QR listo!")
                except Exception as e:
                    st.error(f"Error al generar QR: {e}")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- SECCIÓN 1: REGISTRO ---
    if opcion == "📝 Registro Nuevo":
        st.title("🗳️ Nuevo Registro de Ciudadano")
        if st.session_state.get("is_guest"):
            st.markdown(f'<div class="guest-banner">👋 <b>Modo Invitado:</b> Estás registrando datos para: <b>{usuario.capitalize()}</b></div>', unsafe_allow_html=True)

        with st.form("registro_form", clear_on_submit=False):
            st.subheader("Información Personal")
            col1, col2 = st.columns(2)
            with col1:
                in_nombre = st.text_input("Nombre Completo", value=st.session_state.val_nombre)
                in_cedula = st.text_input("Número de Cédula", value=st.session_state.val_cedula)
                in_telefono = st.text_input("Número de Teléfono", value=st.session_state.val_telefono)
            with col2:
                in_ocupacion = st.text_input("Ocupación", value=st.session_state.val_ocupacion)
                in_direccion = st.text_input("Dirección", value=st.session_state.val_direccion)
                in_barrio = st.text_input("Barrio", value=st.session_state.val_barrio)
            
            c_map1, c_map2 = st.columns(2)
            in_ciudad = c_map1.text_input("Ciudad", value=st.session_state.val_ciudad)
            in_puesto = c_map2.text_input("Puesto de Votación (Opcional)", value=st.session_state.val_puesto)
            
            st.markdown("---")
            enviar = st.form_submit_button("✅ Guardar Registro")

            if enviar:
                st.session_state.val_nombre = in_nombre
                st.session_state.val_cedula = in_cedula
                st.session_state.val_telefono = in_telefono
                st.session_state.val_ocupacion = in_ocupacion
                st.session_state.val_direccion = in_direccion
                st.session_state.val_barrio = in_barrio
                st.session_state.val_ciudad = in_ciudad
                st.session_state.val_puesto = in_puesto

                errores = []
                if not all([in_nombre.strip(), in_cedula.strip(), in_telefono.strip(), in_ocupacion.strip(), 
                            in_direccion.strip(), in_barrio.strip(), in_ciudad.strip()]):
                    errores.append("⚠️ Todos los campos (excepto Puesto) son obligatorios.")
                
                if in_cedula.strip() and not in_cedula.strip().isdigit():
                    errores.append("❌ La Cédula debe contener solo números.")
                
                if in_telefono.strip() and not in_telefono.strip().isdigit():
                    errores.append("❌ El Teléfono debe contener solo números.")

                if errores:
                    for error in errores: st.error(error)
                else:
                    data = {
                        "nombre": in_nombre.strip().upper(), "cedula": in_cedula.strip(),
                        "telefono": in_telefono.strip(), "ocupacion": in_ocupacion.strip().upper(),
                        "direccion": in_direccion.strip().upper(), "barrio": in_barrio.strip().upper(),
                        "ciudad": in_ciudad.strip().upper(), "puesto": in_puesto.strip().upper()
                    }
                    with st.spinner("Guardando registro..."):
                        if save_to_drive(data):
                            st.success(f"✅ ¡Registro de {in_nombre.upper()} guardado!")
                            for campo in campos_form:
                                st.session_state[f"val_{campo}"] = "" if campo != "ciudad" else "BUGA"
                            time.sleep(2)
                            st.rerun()

    # --- SECCIÓN 2: BÚSQUEDA (Restringido) ---
    elif opcion == "🔍 Búsqueda Rápida" and es_admin:
        st.title("🔍 Consulta de Base de Datos")
        df = get_all_data()
        if not df.empty:
            busqueda = st.text_input("Buscar por Nombre o Cédula:").upper()
            if busqueda:
                mask = df.astype(str).apply(lambda row: row.str.contains(busqueda).any(), axis=1)
                st.dataframe(df[mask], use_container_width=True)
            else:
                st.info("Mostrando registros recientes:")
                st.dataframe(df.tail(15), use_container_width=True)
        else: st.warning("No hay datos disponibles.")

    # --- SECCIÓN 3: ESTADÍSTICAS (Restringido) ---
    elif opcion == "📊 Estadísticas" and es_admin:
        st.title("📊 Análisis de Gestión")
        df = get_all_data()
        if not df.empty:
            col_nombre = 'Nombre' if 'Nombre' in df.columns else df.columns[2]
            col_ciudad = 'Ciudad' if 'Ciudad' in df.columns else 'Ciudad'
            col_lider = 'Registrado Por' if 'Registrado Por' in df.columns else df.columns[1]

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Registrados", len(df))
            m2.metric("Ciudades Cubiertas", df[col_ciudad].nunique() if col_ciudad in df.columns else 0)
            m3.metric("Último Registro", df.iloc[-1][col_nombre] if col_nombre in df.columns else "N/A")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Concentración por Ciudad")
                if col_ciudad in df.columns:
                    st.plotly_chart(px.pie(df, names=col_ciudad, color_discrete_sequence=px.colors.sequential.RdPu), use_container_width=True)
            with c2:
                st.subheader("Desempeño por Líder")
                if col_lider in df.columns:
                    st.plotly_chart(px.bar(df[col_lider].value_counts(), color_discrete_sequence=['#D81B60']), use_container_width=True)

            # --- MAPA ---
            st.markdown("---")
            st.subheader("📍 Mapa Geográfico de Registros")
            coords = {
                'BUGA': [3.9009, -76.3008], 'CALI': [3.4516, -76.5320], 'BOGOTA': [4.7110, -74.0721],
                'MEDELLIN': [6.2442, -75.5812], 'PALMIRA': [3.5394, -76.3036], 'TULUA': [4.0847, -76.1954],
                'CARTAGO': [4.7464, -75.9117], 'YUMBO': [3.5411, -76.4911], 'JAMUNDI': [3.2612, -76.5350],
                'SAN PEDRO': [3.9936, -76.2281], 'GUACARI': [3.7633, -76.3325], 'DARIEN': [3.9314, -76.5186]
            }

            if col_ciudad in df.columns:
                map_data = df[col_ciudad].str.strip().str.upper().value_counts().reset_index()
                map_data.columns = ['Ciudad', 'Cantidad']
                map_data['lat'] = map_data['Ciudad'].apply(lambda x: coords.get(x, [3.9, -76.3])[0])
                map_data['lon'] = map_data['Ciudad'].apply(lambda x: coords.get(x, [3.9, -76.3])[1])

                fig_map = px.scatter_mapbox(
                    map_data, lat="lat", lon="lon", size="Cantidad", color="Cantidad",
                    color_continuous_scale="RdPu", size_max=40, zoom=7,
                    mapbox_style="carto-positron", hover_name="Ciudad"
                )
                st.plotly_chart(fig_map, use_container_width=True)
        else: st.info("Sin registros para analizar.")
