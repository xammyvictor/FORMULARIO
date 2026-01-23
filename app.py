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
import numpy as np

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE DISEÑO PULSE (CSS PREMIUM) ---
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

    /* Tarjetas KPI Estilo Pulse */
    .pulse-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
    }
    .pulse-label { color: var(--pulse-slate); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .pulse-value { color: var(--pulse-dark); font-size: 2.2rem; font-weight: 800; margin: 8px 0; line-height: 1; }

    /* Hero Meta Section */
    .hero-section {
        background: var(--pulse-dark);
        color: white;
        padding: 40px;
        border-radius: 32px;
        margin-bottom: 35px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    .hero-big-num { font-size: 4rem; font-weight: 800; color: white !important; line-height: 1; }
    .hero-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
    
    .progress-track {
        background: rgba(255, 255, 255, 0.1);
        height: 16px;
        border-radius: 20px;
        width: 100%;
        margin-top: 25px;
        overflow: hidden;
    }
    .progress-fill {
        background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%);
        height: 100%;
        border-radius: 20px;
        transition: width 1.5s ease-in-out;
    }

    /* Estilo de Ranking */
    .hotspot-tag {
        padding: 4px 12px;
        background: #FCE4EC;
        color: #E91E63;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #F8BBD0;
    }
    .stButton>button { border-radius: 12px !important; background: var(--pulse-pink) !important; color: white !important; font-weight: 700 !important; }
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

# --- NORMALIZACIÓN DE MUNICIPIOS (PARA MAPA DE COROPLETAS) ---
def normalizar_muni(muni):
    m = str(muni).upper().strip()
    # Este mapeo es VITAL para que los datos "encajen" con el dibujo GeoJSON
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "CALIMA": "CALIMA",
        "PALMIRA": "PALMIRA",
        "CARTAGO": "CARTAGO",
        "YUMBO": "YUMBO",
        "ROLDANILLO": "ROLDANILLO",
        "ZARZAL": "ZARZAL",
        "ANDALUCIA": "ANDALUCÍA",
        "FLORIDA": "FLORIDA",
        "PRADERA": "PRADERA",
        "EL CERRITO": "EL CERRITO",
        "GINEBRA": "GINEBRA",
        "LA UNION": "LA UNIÓN",
        "SEVILLA": "SEVILLA",
        "CAICEDONIA": "CAICEDONIA",
        "ANSERMANUEVO": "ANSERMANUEVO",
        "BOLIVAR": "BOLÍVAR",
        "BUENAVENTURA": "BUENAVENTURA",
        "BUGALAGRANDE": "BUGALAGRANDE",
        "CANDELARIA": "CANDELARIA",
        "DAGUA": "DAGUA",
        "EL AGUILA": "EL ÁGUILA",
        "EL CAIRO": "EL CAIRO",
        "EL DOVIO": "EL DOVIO",
        "LA CUMBRE": "LA CUMBRE",
        "LA VICTORIA": "LA VICTORIA",
        "OBANDO": "OBANDO",
        "RESTREPO": "RESTREPO",
        "RIOFRIO": "RIOFRIO",
        "SAN PEDRO": "SAN PEDRO",
        "TORO": "TORO",
        "TRUJILLO": "TRUJILLO",
        "ULLOA": "ULLOA",
        "VERSALLES": "VERSALLES",
        "VIJES": "VIJES",
        "YOTOCO": "YOTOCO"
    }
    return mapping.get(m, m)

# --- CARGA DEL GEOJSON (DIBUJO TERRITORIAL) ---
@st.cache_data(ttl=3600)
def load_valle_geojson():
    # Usamos jsDelivr como fuente primaria por ser más estable que GitHub Raw
    url = "https://cdn.jsdelivr.net/gh/finiterank/mapa-colombia-json@master/valle-del-cauca.json"
    try:
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            return r.json()
    except:
        return None

# --- AUTH ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    params = st.query_params
    if "ref" in params and "ref_checked" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.user_name = params["ref"]
        st.session_state.is_guest = True
        st.session_state.ref_checked = True

    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 100px;'><h1>Pulse Login</h1></div>", unsafe_allow_html=True)
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
                else: st.error("Acceso denegado")
        return False
    return True

if "f_reset" not in st.session_state: st.session_state.f_reset = 0

# --- DASHBOARD ---
if check_auth():
    usuario = st.session_state.user_name
    es_admin = usuario.lower() in ["fabian", "xammy", "brayan"] and not st.session_state.get("is_guest", False)

    st.sidebar.markdown(f"<div style='background:#FCE4EC; padding:20px; border-radius:18px; color:#E91E63; font-weight:800; text-align:center;'>⚡ PULSE | {usuario.upper()}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    opcion = st.sidebar.radio("MENÚ", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    # --- REGISTRO ---
    if opcion == "📝 Registro":
        st.title("🗳️ Nuevo Registro de Ciudadano")
        with st.form(key=f"form_pulse_{st.session_state.f_reset}", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre Completo")
                ced = st.text_input("Cédula")
                tel = st.text_input("Teléfono")
            with c2:
                ocu = st.text_input("Ocupación")
                dire = st.text_input("Dirección")
                bar = st.text_input("Barrio")
            ciu = st.text_input("Municipio", value="BUGA")
            pue = st.text_input("Puesto Votación (Opcional)")
            
            if st.form_submit_button("GUARDAR REGISTRO"):
                if nom and ced and tel:
                    if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dire.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("✅ ¡Registro guardado exitosamente!")
                        st.session_state.f_reset += 1 
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor complete Nombre, Cédula y Teléfono")

    # --- ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas":
        df = get_data()
        if not df.empty:
            st.title("Pulse Analytics | Dashboard Valle del Cauca")
            
            # 1. META HERO
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            st.markdown(f"""
                <div class="hero-section">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <p style="margin:0; font-weight:700; opacity:0.6; font-size:0.8rem; letter-spacing:0.1em; text-transform:uppercase;">Meta Global de Gestión</p>
                            <h1 class="hero-big-num">{total:,}</h1>
                        </div>
                        <div style="text-align:right;">
                            <span class="hero-perc">{perc:.1f}%</span>
                            <p style="margin:0; opacity:0.6; font-size:0.8rem;">Meta: {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="progress-track"><div class="progress-fill" style="width: {perc}%;"></div></div>
                </div>
            """, unsafe_allow_html=True)

            # 2. KPIs
            hoy = datetime.now()
            df['F_S'] = df['Fecha Registro'].dt.date
            v_hoy = len(df[df['F_S'] == hoy.date()])
            v_8d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=8))])
            v_30d = len(df[df['Fecha Registro'] > (hoy - timedelta(days=30))])

            k1, k2, k3, k4 = st.columns(4)
            for col, (lab, val) in zip([k1, k2, k3, k4], [("Hoy", v_hoy), ("8 días", v_8d), ("30 días", v_30d), ("Municipios", df['Ciudad'].nunique())]):
                col.markdown(f"""<div class="pulse-card"><div class="pulse-label">{lab}</div><div class="pulse-value">{val:,}</div></div>""", unsafe_allow_html=True)

            # 3. MAPA DE COROPLETAS
            st.markdown("<br>", unsafe_allow_html=True)
            c_map, c_rank = st.columns([1.6, 1])
            
            with c_map:
                st.subheader("🗺️ Mapa de Coropletas Territorial")
                m_df = df.copy()
                m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_muni)
                map_data = m_df['Municipio_Map'].value_counts().reset_index()
                map_data.columns = ['Municipio', 'Registros']
                
                geojson = load_valle_geojson()
                if geojson:
                    # Crear el dibujo territorial (Choropleth)
                    fig = px.choropleth(
                        map_data, 
                        geojson=geojson, 
                        locations='Municipio',
                        featureidkey="properties.name", # Llave crítica para unir datos con el dibujo
                        color='Registros',
                        color_continuous_scale="Reds", 
                        template="plotly_white",
                        hover_name="Municipio"
                    )
                    # Forzar vista de solo el dibujo del departamento
                    fig.update_geos(
                        fitbounds="locations", 
                        visible=False,
                        projection_type="mercator"
                    )
                    fig.update_layout(
                        margin={"r":0,"t":0,"l":0,"b":0}, 
                        height=580, 
                        coloraxis_showscale=True,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.error("Error al cargar el dibujo del mapa. Mostrando tabla de datos:")
                    st.dataframe(map_data, use_container_width=True, hide_index=True)

            with c_rank:
                st.subheader("🏆 TOP Líderes")
                ranking = df['Registrado Por'].value_counts().reset_index()
                ranking.columns = ['Líder', 'Total']
                for i, row in ranking.head(10).iterrows():
                    st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #F1F5F9;">
                            <span style="font-weight:700; color:#1E293B;">{i+1}. {row['Líder'].upper()}</span>
                            <span class="hotspot-tag">{row['Total']} regs</span>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                sel_lider = st.selectbox("Explorar líder:", ["-- Seleccionar --"] + list(ranking['Líder']))
                if sel_lider != "-- Seleccionar --":
                    st.dataframe(df[df['Registrado Por'] == sel_lider][['Nombre', 'Ciudad']].tail(10), use_container_width=True, hide_index=True)

            # 4. TENDENCIA
            st.markdown("---")
            st.subheader("📈 Actividad de Ingresos")
            trend = df.groupby('F_S').size().reset_index(name='Ingresos')
            fig_t = px.area(trend, x='F_S', y='Ingresos', color_discrete_sequence=['#E91E63'])
            fig_t.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_t, use_container_width=True)

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador Pulse")
        df = get_data()
        if not df.empty:
            q = st.text_input("Buscar por Nombre, Cédula o Ciudad").upper()
            if q:
                res = df[df.astype(str).apply(lambda x: q in x.values, axis=1)]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
