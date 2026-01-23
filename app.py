import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from datetime import datetime, timedelta
import plotly.express as px
import requests
import unicodedata

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# ESTILOS (NO MODIFICADOS)
# =========================================================
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {
    --pulse-pink:#E91E63; --pulse-dark:#0F172A; --pulse-slate:#64748B;
    --pulse-bg:#F8FAFC; --pulse-card-shadow:0 4px 20px rgba(0,0,0,0.04);
}
* { font-family:'Plus Jakarta Sans',sans-serif; }
.stApp { background-color:var(--pulse-bg); }
.pulse-hero{background:var(--pulse-dark);color:white;padding:40px;border-radius:32px;margin-bottom:35px;}
.hero-label{font-size:.8rem;font-weight:700;opacity:.6;letter-spacing:.1em;text-transform:uppercase;}
.hero-value{font-size:4rem;font-weight:800;margin:10px 0;}
.hero-perc{font-size:2.5rem;font-weight:800;color:var(--pulse-pink);}
.pulse-progress-track{background:rgba(255,255,255,.1);height:16px;border-radius:20px;overflow:hidden;}
.pulse-progress-fill{background:linear-gradient(90deg,#E91E63,#FF80AB);height:100%;}
.pulse-kpi-card{background:white;padding:24px;border-radius:24px;border:1px solid #F1F5F9;}
.kpi-label{color:var(--pulse-slate);font-size:.85rem;font-weight:700;text-transform:uppercase;}
.kpi-val{font-size:2.4rem;font-weight:800;}
.rank-item{display:flex;justify-content:space-between;padding:16px;background:white;border-radius:18px;margin-bottom:10px;}
.rank-num{width:32px;height:32px;background:#FCE4EC;color:var(--pulse-pink);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;}
.rank-name{font-weight:700;}
.rank-badge{background:#F8FAFC;padding:6px 14px;border-radius:12px;font-weight:700;}
.stSidebar{background:white!important;}
.stButton>button{border-radius:14px!important;background:var(--pulse-pink)!important;color:white!important;}
.hotspot-pill{padding:4px 12px;background:#FEF2F2;color:#B91C1C;border-radius:20px;font-size:.75rem;font-weight:700;}
</style>""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS
# =========================================================
@st.cache_resource
def get_google_sheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def get_data():
    sh = get_google_sheet_client().open("Base_Datos_Ciudadanos")
    df = pd.DataFrame(sh.sheet1.get_all_records())
    if not df.empty:
        df["Fecha Registro"] = pd.to_datetime(df["Fecha Registro"], errors="coerce")
        df.columns = df.columns.str.strip()
    return df

def save_data(data):
    sh = get_google_sheet_client().open("Base_Datos_Ciudadanos")
    sh.sheet1.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        st.session_state.user_name,
        data["nombre"], data["cedula"], data["telefono"],
        data["ocupacion"], data["direccion"], data["barrio"],
        data["ciudad"], data.get("puesto","")
    ])

# =========================================================
# NORMALIZACIÓN MUNICIPIOS (CLAVE)
# =========================================================
def normalizar_para_mapa(txt):
    if not txt:
        return None
    t = unicodedata.normalize("NFD", txt.upper().strip())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    mapping = {
        "BUGA":"GUADALAJARA DE BUGA",
        "CALI":"SANTIAGO DE CALI",
        "TULUA":"TULUA",
        "JAMUNDI":"JAMUNDI",
        "GUACARI":"GUACARI",
        "ANDALUCIA":"ANDALUCIA",
        "LA UNION":"LA UNION",
        "DARIEN":"CALIMA"
    }
    return mapping.get(t, t)

# =========================================================
# AUTH
# =========================================================
def check_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Acceder"):
            if u.lower() in ["fabian","xammy","brayan","diegomonta"] and p=="1234":
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
        return False
    return True

# =========================================================
# DASHBOARD
# =========================================================
if check_auth():

    opcion = st.sidebar.radio("MENÚ", ["📝 Registro","📊 Estadísticas","🔍 Búsqueda"])

    if opcion == "📊 Estadísticas":
        df = get_data()
        st.title("Pulse Analytics | Valle del Cauca")

        total = len(df)
        perc = min(total/META_REGISTROS*100,100)

        st.markdown(f"""
        <div class="pulse-hero">
            <p class="hero-label">Progreso Global</p>
            <h1 class="hero-value">{total:,}</h1>
            <span class="hero-perc">{perc:.1f}%</span>
            <div class="pulse-progress-track">
                <div class="pulse-progress-fill" style="width:{perc}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ---------------- MAPA ----------------
        st.subheader("📍 Mapa de Calor y Concentración Territorial")

        m_df = df.copy()
        m_df["Municipio_Map"] = m_df["Ciudad"].apply(normalizar_para_mapa)
        map_data = m_df["Municipio_Map"].value_counts().reset_index()
        map_data.columns = ["Municipio","Registros"]

        @st.cache_data
        def load_geo():
            url = "https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson"
            return requests.get(url).json()

        geojson = load_geo()

        fig = px.choropleth(
            map_data,
            geojson=geojson,
            locations="Municipio",
            featureidkey="properties.NOM_MPIO",
            color="Registros",
            color_continuous_scale="YlOrRd"
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=600, margin=dict(l=0,r=0,t=0,b=0))

        st.plotly_chart(fig, use_container_width=True)
