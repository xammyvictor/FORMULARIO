import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURACIÓN DE METAS ---
META_REGISTROS = 12000

# --- SISTEMA DE DISEÑO PULSE (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    :root {
        --pulse-pink: #E91E63;
        --pulse-dark: #0F172A;
        --pulse-slate: #64748B;
        --pulse-bg: #F8FAFC;
    }
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: var(--pulse-bg); }
    .pulse-hero {
        background: var(--pulse-dark);
        color: white;
        padding: 40px;
        border-radius: 32px;
        margin-bottom: 35px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    .hero-value { font-size: 4rem; font-weight: 800; color: white !important; }
    .hero-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
    .pulse-progress-track { background: rgba(255, 255, 255, 0.1); height: 16px; border-radius: 20px; margin-top: 25px; overflow: hidden; }
    .pulse-progress-fill { background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%); height: 100%; transition: width 1.5s ease-in-out; }
    .pulse-kpi-card { background: white; padding: 24px; border-radius: 24px; border: 1px solid #F1F5F9; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); }
    .rank-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: white; border-radius: 18px; margin-bottom: 10px; border: 1px solid #F1F5F9; }
    .hotspot-pill { padding: 4px 12px; background: #FCE4EC; color: #E91E63; border-radius: 20px; font-weight: 700; font-size: 0.75rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

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
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        row = [ts, user, data_dict["nombre"], data_dict["cedula"], data_dict["telefono"],
               data_dict["ocupacion"], data_dict["direccion"], data_dict["barrio"], 
               data_dict["ciudad"], data_dict.get("puesto", "")]
        sh.sheet1.append_row(row)
        return True
    except: return False

# --- NORMALIZACIÓN DEFINITIVA ---
def normalizar_para_mapa(muni):
    m = str(muni).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "CALIMA": "CALIMA",
        "LA UNION": "LA UNIÓN",
        "LA VICTORIA": "LA VICTORIA",
        "RIOFRIO": "RIOFRÍO",
        "ANDALUCIA": "ANDALUCÍA",
        "EL AGUILA": "EL ÁGUILA",
        "BOLIVAR": "BOLÍVAR"
    }
    return mapping.get(m, m)

# --- AUTH ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown("<div style='text-align:center; padding-top: 80px;'><h1>Pulse Analytics</h1><p>Gestión Maria Irma</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Acceder"):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else: st.error("Error")
    st.stop()

# --- DASHBOARD ---
df = get_data()
usuario = st.session_state.user_name
es_admin = usuario.lower() in ["fabian", "xammy", "brayan"]

st.sidebar.title("Pulse Menu")
opcion = st.sidebar.radio("Navegación", ["📝 Registro", "📊 Estadísticas"] if es_admin else ["📝 Registro"])
if st.sidebar.button("Salir"):
    st.session_state.clear()
    st.rerun()

if opcion == "📝 Registro":
    st.title("🗳️ Registro de Ciudadanos")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre")
            ced = st.text_input("Cédula")
        with c2:
            ciu = st.text_input("Municipio", value="BUGA")
            tel = st.text_input("Teléfono")
        if st.form_submit_button("GUARDAR"):
            if nom and ced:
                if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":"","direccion":"","barrio":"","ciudad":ciu.upper()}):
                    st.success("Guardado")
                    time.sleep(1)
                    st.rerun()

elif opcion == "📊 Estadísticas" and not df.empty:
    st.title("Panel de Control | Valle del Cauca")
    
    # Hero Metrics
    total = len(df)
    perc = min((total/META_REGISTROS)*100, 100)
    st.markdown(f"""<div class="pulse-hero"><h1 class="hero-value">{total:,}</h1><span class="hero-perc">{perc:.1f}% de la meta</span><div class="pulse-progress-track"><div class="pulse-progress-fill" style="width:{perc}%"></div></div></div>""", unsafe_allow_html=True)

    # MAP SECTION
    st.subheader("📍 Cobertura Territorial")
    
    # 1. Preparar datos
    m_df = df.copy()
    m_df['Mpio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
    map_counts = m_df.groupby('Mpio_Map').size().reset_index(name='Registros')

    c_map, c_info = st.columns([2, 1])

    with c_map:
        try:
            # 2. Cargar GeoJSON de forma segura
            geo_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
            geo_data = requests.get(geo_url).json()
            
            # Lista de nombres válidos en el mapa (para depurar)
            nombres_validos = [f['properties']['name'] for f in geo_data['features']]
            
            # 3. Crear Mapa
            fig = px.choropleth(
                map_counts,
                geojson=geo_data,
                locations='Mpio_Map',
                featureidkey="properties.name",
                color='Registros',
                color_continuous_scale=[[0, '#FCE4EC'], [0.5, '#F06292'], [1, '#E91E63']],
                template="plotly_white"
            )
            
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500, paper_bgcolor='rgba(0,0,0,0)')
            
            st.plotly_chart(fig, use_container_width=True)

            # 4. Verificación de errores (Solo visible si hay fallos)
            mismos = map_counts[~map_counts['Mpio_Map'].isin(nombres_validos)]
            if not mismos.empty:
                st.error(f"⚠️ Hay {len(mismos)} municipios que el mapa no reconoce:")
                st.write(mismos['Mpio_Map'].tolist())

        except Exception as e:
            st.error(f"Error cargando mapa: {e}")

    with c_info:
        st.write("**Top Municipios**")
        top_m = map_counts.sort_values('Registros', ascending=False).head(8)
        for _, r in top_m.iterrows():
            st.markdown(f"""<div class="rank-item"><b>{r['Mpio_Map']}</b> <span class="hotspot-pill">{r['Registros']}</span></div>""", unsafe_allow_html=True)
