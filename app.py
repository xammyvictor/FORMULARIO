import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# ESTILOS BÁSICOS
# --------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: #F8FAFC; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# GOOGLE SHEETS
# --------------------------------------------------
@st.cache_resource
def get_google_sheet_client():
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

def get_data():
    client = get_google_sheet_client()
    if not client:
        return pd.DataFrame()

    sh = client.open("Base_Datos_Ciudadanos")
    df = pd.DataFrame(sh.sheet1.get_all_records())

    if not df.empty:
        df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        df.columns = [c.strip() for c in df.columns]

    return df

def save_data(data):
    client = get_google_sheet_client()
    if not client:
        return False

    sh = client.open("Base_Datos_Ciudadanos")
    ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    user = st.session_state.get("user_name", "Anonimo")

    row = [
        ts, user, data["nombre"], data["cedula"], data["telefono"],
        data["ocupacion"], data["direccion"], data["barrio"],
        data["ciudad"], data.get("puesto", "")
    ]
    sh.sheet1.append_row(row)
    return True

# --------------------------------------------------
# NORMALIZACIÓN MUNICIPIOS (MATCH EXACTO GEOJSON)
# --------------------------------------------------
def normalizar_para_mapa(muni):
    if pd.isna(muni):
        return None

    m = str(muni).strip().title()

    mapping = {
        "Buga": "Guadalajara De Buga",
        "Cali": "Santiago De Cali",
        "Jamundi": "Jamundí",
        "Tulua": "Tuluá",
        "Guacari": "Guacarí",
        "Darien": "Calima",
        "Palmira": "Palmira",
        "Cartago": "Cartago",
        "Yumbo": "Yumbo",
        "Andalucia": "Andalucía",
        "Buenaventura": "Buenaventura",
        "Bugalagrande": "Bugalagrande",
        "Caicedonia": "Caicedonia",
        "Candelaria": "Candelaria",
        "Dagua": "Dagua",
        "El Cerrito": "El Cerrito",
        "El Dovio": "El Dovio",
        "Florida": "Florida",
        "Ginebra": "Ginebra",
        "La Cumbre": "La Cumbre",
        "La Union": "La Unión",
        "La Victoria": "La Victoria",
        "Obando": "Obando",
        "Pradera": "Pradera",
        "Restrepo": "Restrepo",
        "Riofrio": "Riofrio",
        "Roldanillo": "Roldanillo",
        "San Pedro": "San Pedro",
        "Sevilla": "Sevilla",
        "Toro": "Toro",
        "Trujillo": "Trujillo",
        "Ulloa": "Ulloa",
        "Versalles": "Versalles",
        "Vijes": "Vijes",
        "Yotoco": "Yotoco",
        "Zarzal": "Zarzal"
    }

    return mapping.get(m, m)

# --------------------------------------------------
# CARGA SEGURA DEL GEOJSON (ANTI JSONDecodeError)
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_valle_geojson():
    url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-json/master/valle-del-cauca.json"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# --------------------------------------------------
# AUTH SIMPLE
# --------------------------------------------------
def check_auth():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Pulse Analytics")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")

        if st.button("Acceder"):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else:
                st.error("Acceso denegado")
        return False

    return True

# --------------------------------------------------
# APP PRINCIPAL
# --------------------------------------------------
if check_auth():

    opcion = st.sidebar.radio(
        "MENÚ",
        ["📝 Registro", "📊 Estadísticas"]
    )

    # -----------------------------
    # REGISTRO
    # -----------------------------
    if opcion == "📝 Registro":
        st.subheader("📝 Nuevo Registro")

        with st.form("registro"):
            nom = st.text_input("Nombre")
            ced = st.text_input("Cédula")
            tel = st.text_input("Teléfono")
            ocu = st.text_input("Ocupación")
            dire = st.text_input("Dirección")
            bar = st.text_input("Barrio")
            ciu = st.text_input("Municipio", value="Cali")
            pue = st.text_input("Puesto")

            if st.form_submit_button("Guardar"):
                if nom and ced and tel:
                    save_data({
                        "nombre": nom.upper(),
                        "cedula": ced,
                        "telefono": tel,
                        "ocupacion": ocu.upper(),
                        "direccion": dire.upper(),
                        "barrio": bar.upper(),
                        "ciudad": ciu,
                        "puesto": pue.upper()
                    })
                    st.success("Registro guardado")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Nombre, cédula y teléfono son obligatorios")

    # -----------------------------
    # ESTADÍSTICAS
    # -----------------------------
    if opcion == "📊 Estadísticas":
        df = get_data()

        if df.empty:
            st.warning("No hay datos registrados")
            st.stop()

        st.subheader("📍 Coropleta – Valle del Cauca")

        df['Municipio_Map'] = df['Ciudad'].apply(normalizar_para_mapa)
        map_data = df['Municipio_Map'].value_counts().reset_index()
        map_data.columns = ['Municipio', 'Registros']

        geojson_data = load_valle_geojson()
        if geojson_data is None:
            st.error("No se pudo cargar el mapa del Valle del Cauca")
            st.stop()

        fig = px.choropleth(
            map_data,
            geojson=geojson_data,
            locations="Municipio",
            featureidkey="properties.name",
            color="Registros",
            color_continuous_scale="YlOrRd",
            labels={"Registros": "Total de Registros"},
            template="plotly_white"
        )

        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(
            height=600,
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        st.plotly_chart(fig, use_container_width=True)
