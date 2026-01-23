import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# --- CONFIGURACIÓN GENERAL ---
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE DISEÑO PULSE (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    :root {
        --pulse-pink: #E91E63;
        --pulse-dark: #0F172A;
        --pulse-bg: #F8FAFC;
    }
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: var(--pulse-bg); }
    .pulse-hero {
        background: var(--pulse-dark); color: white; padding: 40px;
        border-radius: 32px; margin-bottom: 35px;
    }
    .hero-value { font-size: 3.5rem; font-weight: 800; color: white !important; margin: 0; }
    .hero-perc { font-size: 2rem; font-weight: 800; color: var(--pulse-pink); }
    .pulse-progress-track { background: rgba(255, 255, 255, 0.1); height: 12px; border-radius: 10px; margin-top: 20px; }
    .pulse-progress-fill { background: linear-gradient(90deg, #E91E63, #FF80AB); height: 100%; border-radius: 10px; }
    .pulse-kpi-card { background: white; padding: 20px; border-radius: 20px; border: 1px solid #F1F5F9; text-align: center; }
    .kpi-val { font-size: 2rem; font-weight: 800; color: var(--pulse-dark); }
    .rank-item { display: flex; justify-content: space-between; padding: 12px; background: white; border-radius: 15px; margin-bottom: 8px; border: 1px solid #F1F5F9; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de credenciales: {e}")
        return None

def get_data():
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
            df.columns = [c.strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def save_data(data_dict):
    client = get_google_sheet_client()
    if not client: return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        row = [ts, user, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
               data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], 
               data_dict["ciudad"], data_dict.get("puesto", "")]
        sh.sheet1.append_row(row)
        return True
    except: return False

# --- NORMALIZACIÓN PARA MAPA ---
def normalizar_para_mapa(muni):
    m = str(muni).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "ANDALUCIA": "ANDALUCÍA",
        "LA UNION": "LA UNIÓN"
    }
    return mapping.get(m, m)

# --- AUTH ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align:center; padding-top:50px;'>Pulse Analytics | Acceso</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.rerun()
                else: st.error("Acceso Denegado")
        return False
    return True

# --- DASHBOARD ---
if check_auth():
    usuario = st.session_state.user_name
    opcion = st.sidebar.radio("MENÚ", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Registro de Ciudadanos")
        with st.form("form_reg", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with c2:
                ocu = st.text_input("Ocupación")
                ciu = st.text_input("Municipio", value="BUGA")
                bar = st.text_input("Barrio")
            if st.form_submit_button("GUARDAR"):
                if nom and ced and tel:
                    if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":"","barrio":bar.upper(),"ciudad":ciu.upper()}):
                        st.success("¡Registro Exitoso!")
                        time.sleep(1)
                        st.rerun()

    elif opcion == "📊 Estadísticas":
        df = get_data()
        if not df.empty:
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            
            # Hero Meta
            st.markdown(f"""
                <div class="pulse-hero">
                    <p style='margin:0; opacity:0.7; letter-spacing:1px;'>PROGRESO DE META</p>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h1 class='hero-value'>{total:,}</h1>
                        <span class='hero-perc'>{perc:.1f}%</span>
                    </div>
                    <div class="pulse-progress-track"><div class="pulse-progress-fill" style="width:{perc}%;"></div></div>
                </div>
            """, unsafe_allow_html=True)

            # Mapa
            st.subheader("📍 Concentración en el Valle del Cauca")
            
            m_df = df.copy()
            m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
            map_data = m_df['Municipio_Map'].value_counts().reset_index()
            map_data.columns = ['Municipio', 'Registros']

            try:
                # URL Alternativa de respaldo para el mapa
                geojson_url = "https://raw.githubusercontent.com/mgaitan/colombia-json/master/valle-del-cauca.json"
                response = requests.get(geojson_url, timeout=10)
                
                if response.status_code == 200:
                    geo_json = response.json()
                    
                    fig = px.choropleth(
                        map_data, 
                        geojson=geo_json, 
                        locations='Municipio',
                        featureidkey="properties.name",
                        color='Registros',
                        color_continuous_scale="Reds",
                        template="plotly_white"
                    )
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("El servidor de mapas no respondió. Verifique la conexión a GitHub.")
            except Exception as e:
                st.error(f"Error al cargar el mapa: {e}")

            # Ranking
            st.write("**Top Líderes**")
            ranking = df['Registrado Por'].value_counts().head(5)
            for lider, cant in ranking.items():
                st.markdown(f"""<div class="rank-item"><span>{lider.upper()}</span><b>{cant} regs</b></div>""", unsafe_allow_html=True)

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador")
        df = get_data()
        if not df.empty:
            q = st.text_input("Buscar por nombre o cédula").upper()
            if q:
                res = df[df.astype(str).apply(lambda x: q in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(50), use_container_width=True)
