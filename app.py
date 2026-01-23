import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta
import requests
import folium
from streamlit_folium import st_folium

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
    st.markdown("<div style='text-align:center; padding-top: 50px;'><h1>Pulse Analytics</h1><p>Gestión Maria Irma</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar al Panel", use_container_width=True):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else: st.error("Acceso Denegado")
    st.stop()

# --- APP ---
usuario = st.session_state.user_name
USUARIOS_ADMIN = ["fabian", "xammy", "brayan", "diegomonta"]
es_admin = usuario.lower() in USUARIOS_ADMIN

with st.sidebar:
    st.markdown(f"### Operador: {usuario.upper()}")
    opcion = st.sidebar.radio("Navegación", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

if opcion == "📝 Registro":
    st.title("🗳️ Registro Ciudadano")
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
        
        if st.form_submit_button("GUARDAR DATOS", use_container_width=True):
            if nom and ced and tel:
                if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dir.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                    st.success("¡Registro Exitoso!")
                    st.session_state.f_res += 1
                    time.sleep(1)
                    st.rerun()
            else: st.warning("Por favor complete los campos obligatorios.")

elif opcion == "📊 Estadísticas":
    df = get_data()
    if df.empty:
        st.info("No hay datos cargados.")
    else:
        st.title("Panel Analytics")
        total = len(df)
        perc = min((total / META_REGISTROS) * 100, 100)
        
        st.markdown(f"""
            <div class="pulse-hero">
                <p class="hero-label">Progreso de Meta Global</p>
                <h1 class="hero-value">{total:,}</h1>
                <p style="margin:0;"><span class="hero-perc">{perc:.1f}%</span> completado (Meta: {META_REGISTROS:,})</p>
            </div>
        """, unsafe_allow_html=True)

        k1, k2, k3 = st.columns(3)
        hoy = datetime.now().date()
        df['F_S'] = df['Fecha Registro'].dt.date
        v_hoy = len(df[df['F_S'] == hoy])
        
        k1.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Hoy</p><p class="kpi-val">{v_hoy}</p></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Municipios</p><p class="kpi-val">{df["Ciudad"].nunique()}</p></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="pulse-kpi-card"><p class="kpi-label">Líderes</p><p class="kpi-val">{df["Registrado Por"].nunique()}</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECCIÓN MAPA (FOLIUM) ---
        st.subheader("📍 Cobertura Territorial")
        
        m_df = df.copy()
        m_df['Ciudad'] = m_df['Ciudad'].astype(str).str.upper().str.strip()
        map_data = m_df['Ciudad'].value_counts().reset_index()
        map_data.columns = ['Municipio', 'Registros']
        
        c_map, c_list = st.columns([2, 1])
        
        with c_map:
            geo_data = load_geojson()
            if geo_data:
                # Centro del mapa (Valle del Cauca aprox)
                m = folium.Map(location=[3.8, -76.3], zoom_start=8, tiles="cartodbpositron")
                
                folium.Choropleth(
                    geo_data=geo_data,
                    name="choropleth",
                    data=map_data,
                    columns=["Municipio", "Registros"],
                    key_on="feature.properties.name", # Coincide con tu JSON properties.name
                    fill_color="YlOrRd",
                    fill_opacity=0.7,
                    line_opacity=0.2,
                    legend_name="Número de Registros",
                    highlight=True
                ).add_to(m)
                
                # Renderizado del mapa
                st_folium(m, width=700, height=500, returned_objects=[])
            else:
                st.error("Error cargando capa geográfica.")

        with c_list:
            st.write("**Top Municipios Activos**")
            for _, r in map_data.head(10).iterrows():
                st.markdown(f'<div class="rank-item"><span class="rank-name">{r["Municipio"]}</span><span class="hotspot-pill">{r["Registros"]}</span></div>', unsafe_allow_html=True)

        # --- LEADERBOARD ---
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
    st.title("🔍 Explorador")
    df = get_data()
    if not df.empty:
        q = st.text_input("Buscar...").upper()
        if q:
            mask = df.astype(str).apply(lambda x: x.str.upper().str.contains(q)).any(axis=1)
            st.dataframe(df[mask], use_container_width=True)
        else:
            st.dataframe(df.tail(100), use_container_width=True)
