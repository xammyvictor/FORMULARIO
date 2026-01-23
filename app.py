# ===============================
# IMPORTS
# ===============================
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide"
)

# ===============================
# ESTILOS
# ===============================
st.markdown("""
<style>
.stApp { background-color: #F8FAFC; }
</style>
""", unsafe_allow_html=True)

# ===============================
# GOOGLE SHEETS
# ===============================
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

def get_data() -> pd.DataFrame:
    client = get_google_sheet_client()
    if not client:
        return pd.DataFrame()

    sh = client.open("Base_Datos_Ciudadanos")
    df = pd.DataFrame(sh.sheet1.get_all_records())

    if not df.empty:
        df['Fecha Registro'] = pd.to_datetime(df['Fecha Registro'], errors='coerce')
        df.columns = [c.strip() for c in df.columns]

    return df

def save_data(data: dict) -> bool:
    client = get_google_sheet_client()
    if not client:
        return False

    sh = client.open("Base_Datos_Ciudadanos")
    ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    user = st.session_state.get("user_name", "Anónimo")

    row = [
        ts, user,
        data["nombre"], data["cedula"], data["telefono"],
        data["ocupacion"], data["direccion"], data["barrio"],
        data["ciudad"], data.get("puesto", "")
    ]

    sh.sheet1.append_row(row)
    return True

# ===============================
# NORMALIZACIÓN MUNICIPIOS
# ===============================
def normalizar_para_mapa(muni: str) -> str:
    m = str(muni).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "TULUA": "TULUÁ",
        "JAMUNDI": "JAMUNDÍ",
        "GUACARI": "GUACARÍ",
        "ANDALUCIA": "ANDALUCÍA",
        "LA UNION": "LA UNIÓN",
        "CALIMA": "CALIMA",
        "DARIEN": "CALIMA"
    }
    return mapping.get(m, m)

# ===============================
# AUTH
# ===============================
def check_auth() -> bool:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Pulse Analytics")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")

        if st.button("Ingresar"):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234"}
            if u.lower() in creds and creds[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u.lower()
                st.rerun()
            else:
                st.error("Acceso denegado")
        return False
    return True

# ===============================
# APP
# ===============================
if check_auth():

    opcion = st.sidebar.radio(
        "Menú",
        ["📝 Registro", "📊 Estadísticas"]
    )

    # ===============================
    # REGISTRO
    # ===============================
    if opcion == "📝 Registro":
        st.title("📝 Nuevo Registro")

        with st.form("registro"):
            nom = st.text_input("Nombre")
            ced = st.text_input("Cédula")
            tel = st.text_input("Teléfono")
            ocu = st.text_input("Ocupación")
            dir = st.text_input("Dirección")
            bar = st.text_input("Barrio")
            ciu = st.text_input("Municipio", value="BUGA")
            pue = st.text_input("Puesto")

            if st.form_submit_button("Guardar"):
                if nom and ced and tel:
                    ok = save_data({
                        "nombre": nom.upper(),
                        "cedula": ced,
                        "telefono": tel,
                        "ocupacion": ocu.upper(),
                        "direccion": dir.upper(),
                        "barrio": bar.upper(),
                        "ciudad": ciu.upper(),
                        "puesto": pue.upper()
                    })
                    if ok:
                        st.success("Registro guardado")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Campos obligatorios incompletos")

    # ===============================
    # ESTADÍSTICAS
    # ===============================
    elif opcion == "📊 Estadísticas":
        df = get_data()
        if df.empty:
            st.warning("Sin datos")
            st.stop()

        st.title("📊 Pulse Analytics")

        # KPIs
        total = len(df)
        hoy = datetime.now().date()
        df['F_S'] = df['Fecha Registro'].dt.date

        c1, c2, c3 = st.columns(3)
        c1.metric("Total", total)
        c2.metric("Hoy", len(df[df['F_S'] == hoy]))
        c3.metric("Municipios", df['Ciudad'].nunique())

        # ===============================
        # MAPA
        # ===============================
        st.subheader("📍 Mapa de Registros")

        m_df = df.copy()
        m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
        map_data = m_df['Municipio_Map'].value_counts().reset_index()
        map_data.columns = ['Municipio', 'Registros']

        try:
            geojson_url = "https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson"
            geojson_data = requests.get(geojson_url).json()

            fig = px.choropleth(
                map_data,
                geojson=geojson_data,
                locations="Municipio",
                featureidkey="properties.NOM_MPIO",
                color="Registros",
                color_continuous_scale="YlOrRd"
            )

            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error en mapa: {e}")
