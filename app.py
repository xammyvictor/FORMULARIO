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
import requests
import json

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Pulse | Maria Irma Analytics",
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
        --pulse-pink-light: #FCE4EC;
        --pulse-dark: #0F172A;
        --pulse-slate: #64748B;
        --pulse-bg: #F8FAFC;
    }

    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .stApp { background-color: var(--pulse-bg); }

    /* Estilo de Tarjetas KPI */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .kpi-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }
    
    .kpi-label { color: var(--pulse-slate); font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { color: var(--pulse-dark); font-size: 2.2rem; font-weight: 800; margin: 8px 0; line-height: 1; }
    .kpi-sub { font-size: 0.8rem; font-weight: 600; color: #10B981; display: flex; align-items: center; gap: 4px; }

    /* Barra de Progreso Meta */
    .hero-goal {
        background: var(--pulse-dark);
        color: white;
        padding: 40px;
        border-radius: 32px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .goal-top { display: flex; justify-content: space-between; align-items: flex-end; }
    .goal-big-num { font-size: 4rem; font-weight: 800; color: white !important; line-height: 1; }
    .goal-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
    
    .progress-track {
        background: rgba(255, 255, 255, 0.1);
        height: 14px;
        border-radius: 20px;
        width: 100%;
        margin-top: 25px;
    }
    .progress-bar {
        background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%);
        height: 100%;
        border-radius: 20px;
        transition: width 1s ease-in-out;
    }

    /* Leaderboard Estilo Pulse */
    .leader-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        background: white;
        border-radius: 16px;
        margin-bottom: 8px;
        border: 1px solid #F1F5F9;
    }
    .leader-info { display: flex; align-items: center; gap: 12px; }
    .leader-rank { width: 32px; height: 32px; background: var(--pulse-pink-light); color: var(--pulse-pink); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.8rem; }
    .leader-name { font-weight: 700; color: #334155; }
    .leader-val { background: #F8FAFC; color: #475569; padding: 4px 12px; border-radius: 8px; font-weight: 700; font-size: 0.8rem; border: 1px solid #E2E8F0; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #E2E8F0; }
    .stButton>button { border-radius: 12px !important; background: var(--pulse-pink) !important; color: white !important; font-weight: 700 !important; border: none !important; width: 100%; height: 3rem; }
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

# --- MAPEO DE MUNICIPIOS (CRÍTICO PARA EL MAPA) ---
def normalize_muni(name):
    n = str(name).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA", "CALI": "SANTIAGO DE CALI", "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ", "GUACARI": "GUACARÍ", "DARIEN": "CALIMA", "PALMIRA": "PALMIRA",
        "CARTAGO": "CARTAGO", "YUMBO": "YUMBO", "ROLDANILLO": "ROLDANILLO", "ZARZAL": "ZARZAL"
    }
    return mapping.get(n, n)

# --- AUTH ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    
    # Check URL Params (Invitados)
    params = st.query_params
    if "ref" in params and "ref_checked" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.user_name = params["ref"]
        st.session_state.is_guest = True
        st.session_state.ref_checked = True

    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding:100px 0;'><h1>Pulse Login</h1></div>", unsafe_allow_html=True)
        with st.container():
            col1, col2, col3 = st.columns([1, 1.2, 1])
            with col2:
                u = st.text_input("Usuario").lower().strip()
                p = st.text_input("Contraseña", type="password")
                if st.button("Entrar"):
                    creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                    if u in creds and creds[u] == p:
                        st.session_state.logged_in = True
                        st.session_state.user_name = u
                        st.session_state.is_guest = False
                        st.rerun()
                    else: st.error("Credenciales incorrectas")
        return False
    return True

if "f_reset" not in st.session_state: st.session_state.f_reset = 0

# --- DASHBOARD ---
if check_auth():
    user = st.session_state.user_name
    es_admin = user in ["fabian", "xammy", "brayan"] and not st.session_state.get("is_guest", False)

    st.sidebar.markdown(f"<div style='background:var(--pulse-pink-light); padding:20px; border-radius:16px; color:var(--pulse-pink); font-weight:800; text-align:center;'>{user.upper()}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    nav = st.sidebar.radio("NAVEGACIÓN", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Salir"):
        st.session_state.clear()
        st.rerun()

    # --- SECCIÓN REGISTRO ---
    if nav == "📝 Registro":
        st.title("🗳️ Nuevo Registro")
        with st.form(key=f"form_{st.session_state.f_reset}"):
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
            pue = st.text_input("Puesto de Votación (Opcional)")
            
            if st.form_submit_button("GUARDAR CIUDADANO"):
                if nom and ced and tel:
                    if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dir.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Registro guardado exitosamente!")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Nombre, Cédula y Teléfono son obligatorios")

    # --- SECCIÓN ESTADÍSTICAS ---
    elif nav == "📊 Estadísticas":
        df = get_data()
        if not df.empty:
            st.title("Pulse Analytics | Valle del Cauca")
            
            # 1. META HERO
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            st.markdown(f"""
                <div class="hero-goal">
                    <div class="goal-top">
                        <div>
                            <p style="margin:0; font-weight:700; opacity:0.6; font-size:0.8rem; letter-spacing:0.1em;">META DE REGISTROS GLOBAL</p>
                            <h1 class="goal-big-num">{total:,}</h1>
                            <p style="margin:0; opacity:0.6;">Sincronización en tiempo real</p>
                        </div>
                        <div style="text-align:right;">
                            <span class="goal-perc">{perc:.1f}%</span>
                            <p style="margin:0; opacity:0.6;">de {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="progress-track"><div class="progress-bar" style="width: {perc}%;"></div></div>
                </div>
            """, unsafe_allow_html=True)

            # 2. KPIs
            hoy = datetime.now()
            df['F_S'] = df['Fecha Registro'].dt.date
            v_hoy = len(df[df['F_S'] == hoy.date()])
            v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            v_15d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=15))])
            v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            metrics = [("Hoy", v_hoy), ("8 días", v_8d), ("15 días", v_15d), ("30 días", v_30d)]
            for col, (lab, val) in zip([k1, k2, k3, k4], metrics):
                col.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-label">{lab}</div>
                        <div class="kpi-value">{val:,}</div>
                        <div class="kpi-sub"><span>▲</span> Activo</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 3. MAPA Y LEADERBOARD
            c_map, c_rank = st.columns([1.6, 1])
            
            with c_map:
                st.subheader("📍 Cobertura Territorial")
                m_df = df.copy()
                m_df['Muni_Map'] = m_df['Ciudad'].apply(normalize_muni)
                map_data = m_df['Muni_Map'].value_counts().reset_index()
                map_data.columns = ['Municipio', 'Registros']
                
                try:
                    # Descargamos el GeoJSON del Valle del Cauca (Solo dibujo de municipios)
                    geojson_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    response = requests.get(geojson_url)
                    geojson = response.json()
                    
                    fig = px.choropleth(
                        map_data, geojson=geojson, locations='Municipio',
                        featureidkey="properties.name", color='Registros',
                        color_continuous_scale="RdPu", template="plotly_white"
                    )
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=550, coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.error("Error al cargar el dibujo del mapa. Mostrando tabla:")
                    st.dataframe(map_data, use_container_width=True)

            with c_rank:
                st.subheader("🏆 Leaderboard")
                rank = df['Registrado Por'].value_counts().reset_index()
                rank.columns = ['Líder', 'Total']
                
                for i, row in rank.head(10).iterrows():
                    st.markdown(f"""
                        <div class="leader-row">
                            <div class="leader-info">
                                <div class="leader-rank">{i+1}</div>
                                <span class="leader-name">{row['Líder'].upper()}</span>
                            </div>
                            <span class="leader-val">{row['Total']} regs</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                sel_lider = st.selectbox("🎯 Ver actividad de líder:", ["-- Seleccione --"] + list(rank['Líder']))
                if sel_lider != "-- Seleccione --":
                    st.dataframe(df[df['Registrado Por'] == sel_lider][['Nombre', 'Ciudad']].tail(10), use_container_width=True, hide_index=True)

            # 4. LÍDERES ACTIVOS (CHIPS)
            st.markdown("---")
            st.subheader("👥 Equipo con Actividad")
            lideres = sorted(df['Registrado Por'].unique())
            chips = "".join([f'<span style="background:#F1F5F9; padding:8px 16px; border-radius:12px; margin:4px; font-weight:600; display:inline-block; border:1px solid #E2E8F0; color:#475569;">{l.upper()}</span>' for l in lideres])
            st.markdown(f"<div>{chips}</div>", unsafe_allow_html=True)

        else: st.info("Sincronizando datos de Google Sheets...")

    # --- SECCIÓN BÚSQUEDA ---
    elif nav == "🔍 Búsqueda":
        st.title("🔍 Explorador de Registros")
        df = get_data()
        if not df.empty:
            q = st.text_input("Buscar por Nombre, Cédula o Ciudad").upper()
            if q:
                res = df[df.astype(str).apply(lambda x: q in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
