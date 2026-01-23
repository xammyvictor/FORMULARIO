import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import qrcode
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Dashboard Maria Irma - Gestión Ciudadana",
    page_icon="📊",
    layout="wide"
)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #333333 !important; }
    h1, h2, h3 { color: #D81B60 !important; text-align: center; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stMetric { background-color: #FCE4EC; padding: 15px; border-radius: 10px; border: 1px solid #F8BBD0; }
    .leader-card { padding: 10px; border-radius: 5px; background-color: #F8F9FA; margin-bottom: 5px; border-left: 5px solid #E91E63; }
    [data-testid="stSidebar"] { background-color: #FCE4EC !important; }
    .stProgress > div > div > div > div { background-color: #E91E63 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Error: Credenciales no encontradas.")
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
            # Convertir fecha a datetime
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame()

def save_to_drive(data_dict, file_name="Base_Datos_Ciudadanos"):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open(file_name)
        worksheet = sh.sheet1
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario_actual = st.session_state.get("user_name", "Desconocido")
        row = [timestamp, usuario_actual, data_dict["nombre"], data_dict["cedula"], 
               data_dict["telefono"], data_dict["ocupacion"], data_dict["direccion"], 
               data_dict["barrio"], data_dict["ciudad"], data_dict.get("puesto", "")]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- LÓGICA DE SESIÓN ---
def check_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # Manejo de referido por URL
    try:
        params = st.query_params
        if "ref" in params and "query_checked" not in st.session_state:
            st.session_state.logged_in = True
            st.session_state.user_name = params["ref"]
            st.session_state.is_guest = True
            st.session_state.query_checked = True
    except: pass

    if not st.session_state.logged_in:
        st.title("🔐 Acceso al Sistema")
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u in creds and creds[u] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u
                    st.session_state.is_guest = False
                    st.rerun()
                else: st.error("Error de acceso")
        return False
    return True

if "form_reset_key" not in st.session_state:
    st.session_state.form_reset_key = 0

# --- APP PRINCIPAL ---
if check_session():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan"]
    es_admin = usuario.lower() in USUARIOS_ADMIN and not st.session_state.get("is_guest", False)

    st.sidebar.title(f"👤 {usuario.capitalize()}")
    opciones = ["📝 Registro", "🔍 Búsqueda", "📊 Estadísticas"] if es_admin else ["📝 Registro"]
    opcion = st.sidebar.radio("Menú", opciones)

    if st.sidebar.button("Salir"):
        st.session_state.clear()
        st.rerun()

    # --- MÓDULO DE REGISTRO ---
    if opcion == "📝 Registro":
        st.title("🗳️ Registro de Ciudadano")
        with st.form(key=f"reg_{st.session_state.form_reset_key}"):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with c2:
                ocu = st.text_input("Ocupación")
                dir = st.text_input("Dirección")
                bar = st.text_input("Barrio")
            ciu = st.text_input("Municipio", value="BUGA")
            pue = st.text_input("Puesto (Opcional)")
            
            if st.form_submit_button("✅ Guardar"):
                if all([nom, ced, tel, ciu]):
                    data = {"nombre": nom.upper(), "cedula": ced, "telefono": tel, 
                            "ocupacion": ocu.upper(), "direccion": dir.upper(), 
                            "barrio": bar.upper(), "ciudad": ciu.upper(), "puesto": pue.upper()}
                    if save_to_drive(data):
                        st.success("Guardado correctamente")
                        st.session_state.form_reset_key += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Complete los campos obligatorios")

    # --- MÓDULO DE ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas":
        st.title("📊 Panel de Control y Metas")
        df = get_all_data()
        
        if not df.empty:
            # 1. BARRA DE PROGRESO Y METRICAS TEMPORALES
            total_actual = len(df)
            porcentaje = min(total_actual / META_REGISTROS, 1.0)
            
            st.subheader(f"Progreso hacia la Meta: {total_actual:,} / {META_REGISTROS:,}")
            st.progress(porcentaje)
            
            # Cálculos de tiempo
            hoy = datetime.now()
            df['Fecha'] = df['Fecha Registro'].dt.date
            reg_hoy = len(df[df['Fecha'] == hoy.date()])
            reg_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            reg_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            reg_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            col_t1.metric("Hoy", f"{reg_hoy}")
            col_t2.metric("Últimos 8 días", f"{reg_8d}")
            col_t3.metric("Últimos 15 días", f"{reg_15d}")
            col_t4.metric("Últimos 30 días", f"{reg_30d}")

            st.markdown("---")

            # 2. RANKING DE LÍDERES E INTERACTIVIDAD
            col_rank, col_map = st.columns([1, 1])
            
            with col_rank:
                st.subheader("🏆 Ranking de Líderes")
                lideres_count = df['Registrado Por'].value_counts().reset_index()
                lideres_count.columns = ['Líder', 'Registros']
                
                # Líderes activos
                lideres_activos = df['Registrado Por'].unique()
                st.info(f"Líderes con actividad: {len(lideres_activos)}")

                # Selección de líder para ver detalles
                seleccionado = st.selectbox("Seleccione un líder para ver sus registros:", 
                                            ["Todos"] + list(lideres_count['Líder']))
                
                if seleccionado == "Todos":
                    st.dataframe(lideres_count, use_container_width=True, hide_index=True)
                else:
                    detalles_lider = df[df['Registrado Por'] == seleccionado][['Fecha Registro', 'Nombre', 'Cédula', 'Ciudad']]
                    st.write(f"Registros de **{seleccionado.capitalize()}**:")
                    st.dataframe(detalles_lider, use_container_width=True, hide_index=True)

            with col_map:
                # 3. MAPA DE CALOR VALLE DEL CAUCA (Municipio)
                st.subheader("📍 Mapa de Calor - Valle del Cauca")
                
                # Agrupar por municipio
                municipios_df = df['Ciudad'].str.strip().str.upper().value_counts().reset_index()
                municipios_df.columns = ['Municipio', 'Cantidad']
                
                # Nota: Para un mapa "dibujado" real sin Google Maps usamos px.choropleth
                # Se requiere un archivo GeoJSON de municipios de Colombia. 
                # Usaremos uno simplificado de una URL pública para el Valle.
                try:
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    
                    fig_mapa = px.choropleth(
                        municipios_df,
                        geojson=geojson_url,
                        locations='Municipio',
                        featureidkey="properties.name", # Depende del GeoJSON
                        color='Cantidad',
                        color_continuous_scale="RdPu",
                        scope="south america",
                        labels={'Cantidad':'Registros'}
                    )
                    fig_mapa.update_geos(fitbounds="locations", visible=False)
                    fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
                    st.plotly_chart(fig_mapa, use_container_width=True)
                except:
                    # Fallback si el GeoJSON falla: Gráfico de burbujas/barras representativo
                    st.write("Cargando mapa... (Visualización Alternativa)")
                    st.plotly_chart(px.bar(municipios_df, x='Municipio', y='Cantidad', color='Cantidad', color_continuous_scale="RdPu"), use_container_width=True)

            # 4. LISTADO DE LÍDERES ACTIVOS
            st.markdown("---")
            st.subheader("👥 Líderes que tuvieron actividad")
            cols_lideres = st.columns(4)
            for i, l in enumerate(sorted(lideres_activos)):
                with cols_lideres[i % 4]:
                    st.markdown(f'<div class="leader-card"><b>{l.upper()}</b></div>', unsafe_allow_html=True)

        else:
            st.warning("No hay datos para mostrar estadísticas.")

    # --- MÓDULO DE BÚSQUEDA ---
    elif opcion == "🔍 Búsqueda" and es_admin:
        st.title("🔍 Búsqueda de Ciudadanos")
        df = get_all_data()
        if not df.empty:
            busq = st.text_input("Nombre o Cédula").upper()
            if busq:
                res = df[df.astype(str).apply(lambda x: busq in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(20), use_container_width=True)
