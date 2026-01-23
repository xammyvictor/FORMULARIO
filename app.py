import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
from datetime import datetime, timedelta
import requests

# --- CONFIGURACIÓN ---
META_REGISTROS = 12000
SHEET_NAME = "Base_Datos_Ciudadanos"

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide"
)

# --- ESTILOS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #F8FAFC; }
    .card { background: white; padding: 20px; border-radius: 20px; border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .metric-val { font-size: 2.5rem; font-weight: 800; color: #0F172A; }
    .metric-lab { font-size: 0.8rem; color: #64748B; text-transform: uppercase; font-weight: 700; }
    .pulse-hero { background: #0F172A; color: white; padding: 30px; border-radius: 24px; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE DATOS ---
@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" not in st.secrets:
            return "missing_secrets"
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        return str(e)

def load_data():
    client = get_client()
    if isinstance(client, str): return pd.DataFrame(), client
    try:
        sh = client.open(SHEET_NAME)
        df = pd.DataFrame(sh.sheet1.get_all_records())
        if not df.empty:
            # Limpiar nombres de columnas
            df.columns = [str(c).strip() for c in df.columns]
            # Intentar convertir fecha
            fecha_col = next((c for c in df.columns if "FECHA" in c.upper()), None)
            if fecha_col:
                df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        return df, "ok"
    except Exception as e:
        return pd.DataFrame(), str(e)

# --- NORMALIZACIÓN DE MUNICIPIOS ---
def fix_muni(m):
    m = str(m).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA", "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ", "TULUA": "TULUÁ", "GUACARI": "GUACARÍ"
    }
    return mapping.get(m, m)

# --- SESIÓN Y LOGIN ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align:center;'>⚡ Pulse Login</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        u = st.text_input("Usuario").lower()
        p = st.text_input("Clave", type="password")
        if st.button("Entrar", use_container_width=True):
            creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
            if u in creds and creds[u] == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u
                st.rerun()
            else: st.error("Credenciales inválidas")
else:
    # --- APP PRINCIPAL ---
    df, status = load_data()
    
    # Barra Lateral
    with st.sidebar:
        st.title("Pulse v2.0")
        st.write(f"👤 **{st.session_state.user_name.upper()}**")
        if status != "ok":
            st.error(f"Error de conexión: {status}")
        else:
            st.success("Conectado a Google Sheets")
        
        menu = st.radio("Menú", ["📊 Estadísticas", "📝 Registro", "🔍 Buscar"])
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    if menu == "📊 Estadísticas":
        if df.empty:
            st.info("No hay datos todavía. Empieza registrando a alguien.")
        else:
            st.title("Panel de Control")
            
            # Hero Meta
            total = len(df)
            progreso = min((total/META_REGISTROS)*100, 100)
            st.markdown(f"""
                <div class="pulse-hero">
                    <p style='margin:0; opacity:0.7;'>TOTAL GESTIONADO</p>
                    <h1 style='font-size:3.5rem; margin:0;'>{total:,} <span style='font-size:1.5rem; color:#E91E63;'>/ {META_REGISTROS:,}</span></h1>
                    <div style='background:rgba(255,255,255,0.1); height:10px; border-radius:10px; margin-top:15px;'>
                        <div style='background:#E91E63; width:{progreso}%; height:100%; border-radius:10px;'></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # KPIs
            c1, c2, c3 = st.columns(3)
            # Buscar columnas dinámicamente
            ciu_col = next((c for c in df.columns if "CIUDAD" in c.upper() or "MUNIC" in c.upper()), "Ciudad")
            usu_col = next((c for c in df.columns if "REGISTRADO" in c.upper() or "USER" in c.upper() or "USUARIO" in c.upper()), "Registrado Por")
            
            with c1: st.markdown(f'<div class="card"><p class="metric-lab">Municipios</p><p class="metric-val">{df[ciu_col].nunique() if ciu_col in df else 0}</p></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="card"><p class="metric-lab">Operadores</p><p class="metric-val">{df[usu_col].nunique() if usu_col in df else 0}</p></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="card"><p class="metric-lab">Cobertura</p><p class="metric-val">{int(progreso)}%</p></div>', unsafe_allow_html=True)

            # Mapa
            st.subheader("📍 Mapa de Concentración")
            try:
                map_df = df.copy()
                map_df['M_MAP'] = map_df[ciu_col].apply(fix_muni)
                counts = map_df['M_MAP'].value_counts().reset_index()
                counts.columns = ['Municipio', 'Cantidad']
                
                geo_url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-js/master/colombia-municipios.json"
                geojson = requests.get(geo_url).json()
                
                fig = px.choropleth(
                    counts, geojson=geojson, locations='Municipio', 
                    featureidkey="properties.name", color='Cantidad',
                    color_continuous_scale="Reds", template="plotly_white"
                )
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("El mapa no pudo cargar, mostrando tabla de municipios:")
                st.dataframe(counts)

    elif menu == "📝 Registro":
        st.title("Nuevo Ciudadano")
        st.info("Esta sección requiere que la función save_data esté configurada correctamente.")
        # Aquí iría el formulario (puedes copiar el del código anterior)

    elif menu == "🔍 Buscar":
        st.title("Explorador de Datos")
        search = st.text_input("Buscar por nombre, cédula o municipio...")
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            st.dataframe(df[mask])
        else:
            st.dataframe(df.head(50))
