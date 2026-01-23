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
BASE_URL = "https://formulario-skccey4ttaounxkvpa39sv.streamlit.app/"
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CSS (SIN CAMBIOS)
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
* { font-family: 'Plus Jakarta Sans', sans-serif; }
.stApp { background-color: #F8FAFC; }
.stSidebar { background-color: white !important; }
.stButton>button {
    border-radius: 14px;
    background: #E91E63 !important;
    font-weight: 700 !important;
    color: white !important;
    border: none !important;
    width: 100%;
    height: 3.2rem;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# GOOGLE SHEETS
# --------------------------------------------------
@st.cache_resource
def get_google_sheet_client():
    try:
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
            df.columns = [c.strip() for c in df.columns]
            df["Fecha Registro"] = pd.to_datetime(df["Fecha Registro"], errors="coerce")
        return df
    except:
        return pd.DataFrame()

def save_data(data):
    client = get_google_sheet_client()
    if not client:
        return False
    try:
        sh = client.open("Base_Datos_Ciudadanos")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = st.session_state.get("user_name", "Anonimo")
        row = [
            ts, user,
            data["nombre"], data["cedula"], data["telefono"],
            data["ocupacion"], data["direccion"], data["barrio"],
            data["ciudad"], data.get("puesto", "")
        ]
        sh.sheet1.append_row(row)
        return True
    except:
        return False

# --------------------------------------------------
# NORMALIZACIÓN MUNICIPIOS
# --------------------------------------------------
def normalizar_para_mapa(m):
    m = str(m).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "PALMIRA": "PALMIRA",
        "CARTAGO": "CARTAGO",
        "YUMBO": "YUMBO",
        "ANDALUCIA": "ANDALUCÍA",
        "BUENAVENTURA": "BUENAVENTURA"
    }
    return mapping.get(m, m)

# --------------------------------------------------
# AUTH
# --------------------------------------------------
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
        st.markdown(
            "<div style='text-align:center; padding-top: 80px;'>"
            "<h1>Pulse Analytics</h1><p>Gestión Maria Irma</p></div>",
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Panel"):
                creds = {
                    "fabian": "1234",
                    "xammy": "1234",
                    "brayan": "1234",
                    "diegomonta": "1234"
                }
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.session_state.is_guest = False
                    st.rerun()
                else:
                    st.error("Acceso Denegado")
        return False
    return True

if "f_reset" not in st.session_state:
    st.session_state.f_reset = 0

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
if check_auth():

    usuario = st.session_state.user_name
    es_admin = usuario in ["fabian", "xammy", "brayan"]

    st.sidebar.markdown(
        f"<b>Usuario:</b><br>{usuario.upper()}",
        unsafe_allow_html=True
    )

    opcion = st.sidebar.radio(
        "MENÚ",
        ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"]
    )

    if st.sidebar.button("Salir"):
        st.session_state.clear()
        st.rerun()

    # --------------------------------------------------
    # REGISTRO
    # --------------------------------------------------
    if opcion == "📝 Registro":
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
            pue = st.text_input("Puesto (Opcional)")

            if st.form_submit_button("GUARDAR REGISTRO"):
                if nom and ced and tel:
                    if save_data({
                        "nombre": nom.upper(),
                        "cedula": ced,
                        "telefono": tel,
                        "ocupacion": ocu.upper(),
                        "direccion": dir.upper(),
                        "barrio": bar.upper(),
                        "ciudad": ciu.upper(),
                        "puesto": pue.upper()
                    }):
                        st.success("Registro guardado")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Complete Nombre, Cédula y Teléfono")

    # --------------------------------------------------
    # ESTADÍSTICAS (MAPA CORREGIDO)
    # --------------------------------------------------
    elif opcion == "📊 Estadísticas":

        st.title("📊 Pulse Analytics | Valle del Cauca")

        df = get_data()
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            df["Municipio_Map"] = df["Ciudad"].apply(normalizar_para_mapa)
            map_data = df["Municipio_Map"].value_counts().reset_index()
            map_data.columns = ["Municipio", "Registros"]

            c_map, _ = st.columns([2, 1])

            with c_map:
                geojson_url = (
    "https://raw.githubusercontent.com/"
    "caticoa3/colombia_mapa/master/"
    "co_2018_MGN_MPIO_POLITICO.geojson"
)
geojson_data = requests.get(geojson_url).json()

fig = px.choropleth(
    map_data,
    geojson=geojson_data,
    locations="Municipio",
    featureidkey="properties.NOM_MPIO",
    color="Registros",
    color_continuous_scale="YlOrRd",
    template="plotly_white"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=600)

st.plotly_chart(fig, use_container_width=True)


    # --------------------------------------------------
    # BÚSQUEDA
    # --------------------------------------------------
    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Registros")

        df = get_data()
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            q = st.text_input("Buscar...").upper()
            if q:
                res = df[df.astype(str).apply(
                    lambda x: x.str.upper().str.contains(q, na=False),
                    axis=1
                )]
                st.dataframe(res, use_container_width=True)
            else:
                st.dataframe(df.tail(100), use_container_width=True)
