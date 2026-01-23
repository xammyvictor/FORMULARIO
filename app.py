import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
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

# --- SISTEMA DE DISEÑO PULSE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    .main { background-color: #F8FAFC; }
    div.block-container { padding-top: 2rem; }
    
    .pulse-hero {
        background: #0F172A;
        color: white;
        padding: 30px;
        border-radius: 24px;
        margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .hero-label { font-size: 0.8rem; font-weight: 700; opacity: 0.7; text-transform: uppercase; }
    .hero-value { font-size: 3.5rem; font-weight: 800; line-height: 1; margin: 10px 0; }
    .hero-perc { font-size: 2rem; font-weight: 800; color: #E91E63; }
    
    .pulse-kpi-card {
        background: white;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .kpi-label { color: #64748B; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .kpi-val { color: #0F172A; font-size: 2rem; font-weight: 800; }

    .rank-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        background: white;
        border-radius: 15px;
        margin-bottom: 8px;
        border: 1px solid #F1F5F9;
    }
    .rank-name { font-weight: 600; color: #1E293B; font-size: 0.85rem; }
    .hotspot-pill { padding: 4px 10px; background: #FEF2F2; color: #B91C1C; border-radius: 20px; font-size: 0.7rem; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    if "gcp_service_account" not in st.secrets:
        return None
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except:
        return None

def get_data():
    client = get_google_sheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        return df
    except:
        return pd.DataFrame()

# --- CARGA CACHEDA DEL MAPA (Crítico para evitar pantalla blanca) ---
@st.cache_data(ttl=3600)
def load_geojson():
    url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-js/master/colombia-municipios.json"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except:
        return None

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

# --- AUTENTICACIÓN ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div style='text-align:center; padding-top: 50px;'><h1>Pulse Analytics</h1><p>Ingreso al Sistema</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Acceder", use_container_width=True):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else: st.error("Usuario o contraseña incorrectos")
    st.stop()

# --- PANEL PRINCIPAL ---
usuario = st.session_state.user_name
USUARIOS_ADMIN = ["fabian", "xammy", "brayan", "diegomonta"]
es_admin = usuario.lower() in USUARIOS_ADMIN

with st.sidebar:
    st.markdown(f"### Operador: {usuario.upper()}")
    opcion = st.radio("Menú", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

if opcion == "📝 Registro":
    st.title("🗳️ Nuevo Registro")
    if "f_res" not in st.session_state: st.session_state.f_res = 0
    with st.form(key=f"form_{st.session_state.f_res}"):
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
        
        if st.form_submit_button("GUARDAR REGISTRO", use_container_width=True):
            if nom and ced and tel:
                if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dir.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                    st.success("¡Registro guardado!")
                    st.session_state.f_res += 1
                    time.sleep(1)
                    st.rerun()
            else: st.warning("Nombre, Cédula y Teléfono son obligatorios")

elif opcion == "📊 Estadísticas":
    df = get_data()
    if df.empty:
        st.info("No hay datos todavía. Registra un ciudadano para ver las métricas.")
    else:
        st.title("Estadísticas de Gestión")
        
        # --- HERO METRICS ---
        total = len(df)
        perc = min((total / META_REGISTROS) * 100, 100)
        st.markdown(f"""
            <div class="pulse-hero">
                <p class="hero-label">Total Gestión Global</p>
                <h1 class="hero-value">{total:,}</h1>
                <p style="margin:0;"><span class="hero-perc">{perc:.1f}%</span> de la meta final ({META_REGISTROS:,})</p>
            </div>
        """, unsafe_allow_html=True)

        # KPIs
        k1, k2, k3 = st.columns(3)
        hoy = datetime.now().date()
        df['F_S'] = df['Fecha Registro'].dt.date
        v_hoy = len(df[df['F_S'] == hoy])
        
        k1.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Registros Hoy</p><p class="kpi-val">{v_hoy}</p></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Municipios</p><p class="kpi-val">{df["Ciudad"].nunique()}</p></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Meta Diaria</p><p class="kpi-val">150</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECCIÓN MAPA ---
        st.subheader("📍 Concentración por Municipio")
        
        m_df = df.copy()
        m_df['M_MAP'] = m_df['Ciudad'].astype(str).str.upper().str.strip()
        map_data = m_df['M_MAP'].value_counts().reset_index()
        map_data.columns = ['Municipio', 'Registros']
        
        col_map, col_list = st.columns([2, 1])
        
        with col_map:
            geo_data = load_geojson()
            if geo_data:
                fig = px.choropleth(
                    map_data, geojson=geo_data, locations='Municipio',
                    featureidkey="properties.name", color='Registros',
                    color_continuous_scale="Reds", template="plotly_white"
                )
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(
                    margin={"r":0,"t":0,"l":0,"b":0}, 
                    height=450,
                    # FORZAR RENDERIZADO SVG PARA EVITAR PANTALLA BLANCA
                    dragmode=False 
                )
                # Configuración para evitar problemas de WebGL
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': False})
            else:
                st.error("No se pudo cargar la capa del mapa. Verifica tu conexión.")

        with col_list:
            st.write("**Top 10 Municipios**")
            for _, row in map_data.head(10).iterrows():
                st.markdown(f"""
                    <div class="rank-item">
                        <span class="rank-name">{row['Municipio']}</span>
                        <span class="hotspot-pill">{row['Registros']}</span>
                    </div>
                """, unsafe_allow_html=True)

        # --- RANKING OPERADORES ---
        st.markdown("---")
        st.subheader("🏆 Leaderboard")
        rank = df['Registrado Por'].value_counts().reset_index()
        rank.columns = ['Líder', 'Total']
        
        cols = st.columns(4)
        for i, (idx, row) in enumerate(rank.head(4).iterrows()):
            cols[i].markdown(f"""
                <div class="pulse-kpi-card" style="text-align:center;">
                    <p class="kpi-label">#{i+1} {str(row['Líder']).upper()}</p>
                    <p class="kpi-val" style="color:#E91E63;">{row['Total']}</p>
                </div>
            """, unsafe_allow_html=True)

elif opcion == "🔍 Búsqueda":
    st.title("🔍 Explorador de Registros")
    df = get_data()
    if not df.empty:
        q = st.text_input("Buscar por nombre, cédula o municipio...").upper()
        if q:
            mask = df.astype(str).apply(lambda x: x.str.upper().str.contains(q)).any(axis=1)
            st.dataframe(df[mask], use_container_width=True)
        else:
            st.dataframe(df.tail(100), use_container_width=True)
