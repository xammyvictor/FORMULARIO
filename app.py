import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests

# --- CONFIGURACIÓN GENERAL ---
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
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
    .hero-value { font-size: 4rem; font-weight: 800; line-height: 1; color: white !important; }
    .hero-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
    
    .pulse-progress-track {
        background: rgba(255, 255, 255, 0.1);
        height: 16px;
        border-radius: 20px;
        margin-top: 25px;
        overflow: hidden;
    }
    .pulse-progress-fill {
        background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%);
        height: 100%;
        transition: width 1.5s ease-in-out;
    }

    .pulse-kpi-card {
        background: white;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #F1F5F9;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    }
    .kpi-label { color: var(--pulse-slate); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; }
    .kpi-val { color: var(--pulse-dark); font-size: 2.4rem; font-weight: 800; }

    .rank-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        background: white;
        border-radius: 18px;
        margin-bottom: 10px;
        border: 1px solid #F1F5F9;
    }
    .hotspot-pill {
        padding: 4px 12px;
        background: #FCE4EC;
        color: #E91E63;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
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

# --- NORMALIZACIÓN PARA EL MAPA ---
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
        "ANDALUCIA": "ANDALUCÍA",
    }
    return mapping.get(m, m)

# --- SISTEMA DE AUTENTICACIÓN ---
def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 80px;'><h1>Pulse Analytics</h1><p>Gestión Maria Irma</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Panel"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.rerun()
                else: st.error("Acceso Denegado")
        return False
    return True

# --- LÓGICA PRINCIPAL ---
if check_auth():
    usuario = st.session_state.user_name
    es_admin = usuario.lower() in ["fabian", "xammy", "brayan"]
    
    st.sidebar.markdown(f"<div style='background:#F1F5F9; padding:20px; border-radius:18px; margin-bottom:20px;'><p style='margin:0; font-size:0.75rem; font-weight:700; color:#64748B;'>SESIÓN PULSE</p><p style='margin:0; font-size:1.1rem; font-weight:800; color:#0F172A;'>{usuario.upper()}</p></div>", unsafe_allow_html=True)
    
    opciones = ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"]
    opcion = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

    if st.sidebar.button("Salir"):
        st.session_state.clear()
        st.rerun()

    # --- VISTA: REGISTRO ---
    if opcion == "📝 Registro":
        st.title("🗳️ Nuevo Registro")
        if "f_reset" not in st.session_state: st.session_state.f_reset = 0
        
        with st.form(key=f"form_pulse_{st.session_state.f_reset}"):
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
            
            if st.form_submit_button("GUARDAR REGISTRO"):
                if nom and ced and tel:
                    payload = {"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dir.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}
                    if save_data(payload):
                        st.success("¡Registro guardado exitosamente!")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Por favor complete Nombre, Cédula y Teléfono")

    # --- VISTA: ESTADÍSTICAS ---
    elif opcion == "📊 Estadísticas":
        df = get_data()
        if not df.empty:
            st.title("Pulse Analytics | Valle del Cauca")
            
            # Hero Metrics
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            st.markdown(f"""
                <div class="pulse-hero">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <p style="font-size: 0.8rem; font-weight: 700; opacity: 0.6; letter-spacing: 0.1em; text-transform: uppercase;">Progreso Global</p>
                            <h1 class="hero-value">{total:,}</h1>
                        </div>
                        <div style="text-align:right;">
                            <span class="hero-perc">{perc:.1f}%</span>
                            <p style="margin:0; opacity:0.6; font-size:0.8rem;">Meta: {META_REGISTROS:,}</p>
                        </div>
                    </div>
                    <div class="pulse-progress-track"><div class="pulse-progress-fill" style="width: {perc}%;"></div></div>
                </div>
            """, unsafe_allow_html=True)

            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            hoy = datetime.now().date()
            v_hoy = len(df[df['Fecha Registro'].dt.date == hoy])
            
            for col, (lab, val) in zip([k1, k2, k3, k4], [("Hoy", v_hoy), ("Total", total), ("Municipios", df['Ciudad'].nunique()), ("Líderes", df['Registrado Por'].nunique())]):
                col.markdown(f"""<div class="pulse-kpi-card"><div class="kpi-label">{lab}</div><div class="kpi-val">{val:,}</div></div>""", unsafe_allow_html=True)

            # --- SECCIÓN MAPA OPTIMIZADO ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📍 Concentración Territorial")
            
            m_df = df.copy()
            m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
            map_counts = m_df.groupby('Municipio_Map').size().reset_index(name='Registros')

            c_map, c_list = st.columns([2, 1])

            with c_map:
                try:
                    # GeoJSON optimizado para el Valle del Cauca
                    url_geo = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
                    
                    fig = px.choropleth(
                        map_counts, geojson=url_geo, locations='Municipio_Map',
                        featureidkey="properties.name",
                        color='Registros',
                        color_continuous_scale=[[0, '#FCE4EC'], [0.5, '#F06292'], [1, '#E91E63']],
                        template="plotly_white"
                    )
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.error("Error al cargar el mapa. Verifique la conexión.")

            with c_list:
                st.write("**Top Municipios**")
                for _, row in map_counts.sort_values('Registros', ascending=False).head(6).iterrows():
                    st.markdown(f"""
                        <div class="rank-item">
                            <span style="font-weight:700;">{row['Municipio_Map']}</span>
                            <span class="hotspot-pill">{row['Registros']} regs</span>
                        </div>
                    """, unsafe_allow_html=True)

    # --- VISTA: BÚSQUEDA ---
    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Datos")
        df = get_data()
        if not df.empty:
            busqueda = st.text_input("Buscar por Nombre, Cédula o Municipio").upper()
            if busqueda:
                resultado = df[df.astype(str).apply(lambda x: busqueda in x.values, axis=1)]
                st.dataframe(resultado, use_container_width=True)
            else:
                st.dataframe(df.tail(50), use_container_width=True)
