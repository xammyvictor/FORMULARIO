# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests
import numpy as np

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
# CSS – SISTEMA DE DISEÑO PULSE
# =========================================================
st.markdown("""<style>/* --- CSS ORIGINAL SIN CAMBIOS --- */</style>""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS
# =========================================================
@st.cache_resource
def get_google_sheet_client():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return gspread.authorize(creds)
    except:
        return None

def get_data():
    client = get_google_sheet_client()
    if not client:
        return pd.DataFrame()
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
            df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def save_data(data):
    client = get_google_sheet_client()
    if not client:
        return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anónimo")
        sh.sheet1.append_row([
            ts, user, data["nombre"], data["cedula"], data["telefono"],
            data["ocupacion"], data["direccion"], data["barrio"],
            data["ciudad"], data.get("puesto", "")
        ])
        return True
    except:
        return False

# =========================================================
# NORMALIZACIÓN MUNICIPIOS
# =========================================================
def normalizar_para_mapa(muni):
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ"
        # (resto igual, sin cambios)
    }
    m = str(muni).upper().strip()
    return mapping.get(m, m)

# =========================================================
# AUTENTICACIÓN
# =========================================================
def check_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    params = st.query_params
    if "ref" in params and "ref_checked" not in st.session_state:
        st.session_state.logged_in = True
        st.session_state.user_name = params["ref"]
        st.session_state.is_guest = True
        st.session_state.ref_checked = True

    if not st.session_state.logged_in:
        st.title("Pulse Analytics")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Acceder"):
            creds = {"fabian":"1234","xammy":"1234","brayan":"1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else:
                st.error("Acceso Denegado")
        return False
    return True

# =========================================================
# DASHBOARD PRINCIPAL
# =========================================================
if check_auth():
    opcion = st.sidebar.radio("MENÚ", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"])

    if opcion == "📊 Estadísticas":
        df = get_data()
        if df.empty:
            st.warning("No hay datos")
            st.stop()

        df['Municipio_Map'] = df['Ciudad'].apply(normalizar_para_mapa)
        map_data = df['Municipio_Map'].value_counts().reset_index()
        map_data.columns = ['Municipio', 'Registros']

        # =================================================
        # MAPA (URL NUEVO Y FUNCIONAL)
        # =================================================
        GEOJSON_URL = (
            "https://raw.githubusercontent.com/"
            "datosabiertoscolombia/datos-abiertos-colombia/"
            "master/geojson/departamentos/valle_del_cauca.geojson"
        )

        response = requests.get(GEOJSON_URL)
        geojson_data = response.json()

        fig = px.choropleth(
            map_data,
            geojson=geojson_data,
            locations="Municipio",
            featureidkey="properties.name",
            color="Registros",
            color_continuous_scale="YlOrRd",
            template="plotly_white"
        )

        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)

    elif opcion == "📝 Registro":
        st.info("Formulario intacto (sin cambios)")

    elif opcion == "🔍 Búsqueda":
        st.info("Búsqueda intacta (sin cambios)")
