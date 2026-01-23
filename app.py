import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import numpy as np

# --- CONFIGURACIÓN GENERAL ---
META_REGISTROS = 12000

st.set_page_config(
    page_title="Maria Irma | Pulse Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE DISEÑO PULSE (CSS PERSONALIZADO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    :root {
        --pulse-pink: #E91E63;
        --pulse-dark: #0F172A;
        --pulse-slate: #64748B;
        --pulse-bg: #F8FAFC;
        --pulse-card-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
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
    .hero-label { font-size: 0.8rem; font-weight: 700; opacity: 0.6; text-transform: uppercase; }
    .hero-value { font-size: 4rem; font-weight: 800; line-height: 1; margin: 10px 0; color: white !important; }
    .hero-perc { font-size: 2.5rem; font-weight: 800; color: var(--pulse-pink); }
    
    .pulse-progress-track { background: rgba(255, 255, 255, 0.1); height: 16px; border-radius: 20px; width: 100%; margin-top: 25px; overflow: hidden; }
    .pulse-progress-fill { background: linear-gradient(90deg, #E91E63 0%, #FF80AB 100%); height: 100%; border-radius: 20px; transition: width 1.5s; }

    .pulse-kpi-card { background: white; padding: 24px; border-radius: 24px; border: 1px solid #F1F5F9; box-shadow: var(--pulse-card-shadow); }
    .kpi-label { color: var(--pulse-slate); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-val { color: var(--pulse-dark); font-size: 2.4rem; font-weight: 800; line-height: 1; }

    .rank-item { display: flex; justify-content: space-between; align-items: center; padding: 14px; background: white; border-radius: 18px; margin-bottom: 10px; border: 1px solid #F1F5F9; }
    .rank-num { width: 32px; height: 32px; background: #FCE4EC; color: var(--pulse-pink); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; }
    .rank-name { font-weight: 700; color: #1E293B; font-size: 0.9rem; }
    .rank-badge { background: #F8FAFC; color: #64748B; padding: 6px 12px; border-radius: 10px; font-weight: 700; font-size: 0.75rem; border: 1px solid #E2E8F0; }

    .hotspot-pill { padding: 4px 10px; background: #FEF2F2; color: #B91C1C; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("⚠️ Configuración faltante: 'gcp_service_account' no encontrada en st.secrets.")
        return None
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Error de autenticación: {e}")
        return None

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
    except Exception as e:
        st.error(f"❌ Error al leer datos: {e}")
        return pd.DataFrame()

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

def normalizar_para_mapa(muni):
    m = str(muni).upper().strip()
    mapping = {
        "BUGA": "GUADALAJARA DE BUGA",
        "CALI": "SANTIAGO DE CALI",
        "JAMUNDI": "JAMUNDÍ",
        "TULUA": "TULUÁ",
        "GUACARI": "GUACARÍ",
        "DARIEN": "CALIMA",
        "ANDALUCIA": "ANDALUCÍA",
        "LA UNION": "LA UNIÓN",
        "RIOFRIO": "RIOFRIO",
        "EL CERRITO": "EL CERRITO"
    }
    return mapping.get(m, m)

def check_auth():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<div style='text-align:center; padding-top: 50px;'><h1>Pulse Analytics</h1><p>Gestión Territorial</p></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                creds = {"fabian": "1234", "xammy": "1234", "brayan": "1234", "diegomonta": "1234"}
                if u.lower() in creds and creds[u.lower()] == p:
                    st.session_state.logged_in = True
                    st.session_state.user_name = u.lower()
                    st.rerun()
                else: st.error("Acceso Incorrecto")
        return False
    return True

if "f_reset" not in st.session_state: st.session_state.f_reset = 0

# --- DASHBOARD ---
if check_auth():
    usuario = st.session_state.user_name
    USUARIOS_ADMIN = ["fabian", "xammy", "brayan", "diegomonta"]
    es_admin = usuario.lower() in USUARIOS_ADMIN

    st.sidebar.markdown(f"<div style='background:white; padding:15px; border-radius:15px; margin-bottom:20px;'><p style='margin:0; font-size:0.7rem; color:#64748B;'>OPERADOR</p><p style='margin:0; font-size:1rem; font-weight:800;'>{usuario.upper()}</p></div>", unsafe_allow_html=True)
    opcion = st.sidebar.radio("Navegación", ["📝 Registro", "📊 Estadísticas", "🔍 Búsqueda"] if es_admin else ["📝 Registro"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

    if opcion == "📝 Registro":
        st.title("🗳️ Nuevo Registro")
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
            
            if st.form_submit_button("GUARDAR"):
                if nom and ced and tel:
                    if save_data({"nombre":nom.upper(),"cedula":ced,"telefono":tel,"ocupacion":ocu.upper(),"direccion":dir.upper(),"barrio":bar.upper(),"ciudad":ciu.upper(),"puesto":pue.upper()}):
                        st.success("¡Guardado correctamente!")
                        st.session_state.f_reset += 1
                        time.sleep(1)
                        st.rerun()
                else: st.warning("Nombre, Cédula y Teléfono son obligatorios.")

    elif opcion == "📊 Estadísticas":
        df = get_data()
        if df.empty:
            st.warning("📭 No hay datos disponibles para mostrar estadísticas. Asegúrate de que el Google Sheet tenga registros.")
        else:
            st.title("Pulse Analytics | Valle del Cauca")
            
            # --- HERO ---
            total = len(df)
            perc = min((total / META_REGISTROS) * 100, 100)
            st.markdown(f"""
                <div class="pulse-hero">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <p class="hero-label">Gestión Global</p>
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

            # --- KPIs ---
            hoy = datetime.now().date()
            df['F_S'] = df['Fecha Registro'].dt.date
            v_hoy = len(df[df['F_S'] == hoy])
            v_8d = len(df[df['Fecha Registro'] > (datetime.now() - timedelta(days=8))])
            
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="pulse-kpi-card"><div class="kpi-label">Registros Hoy</div><div class="kpi-val">{v_hoy}</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="pulse-kpi-card"><div class="kpi-label">Últimos 8 días</div><div class="kpi-val">{v_8d}</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="pulse-kpi-card"><div class="kpi-label">Cobertura Territorial</div><div class="kpi-val">{df["Ciudad"].nunique()}</div></div>', unsafe_allow_html=True)

            # --- MAPA ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📍 Concentración Territorial")
            
            m_df = df.copy()
            m_df['Municipio_Map'] = m_df['Ciudad'].apply(normalizar_para_mapa)
            map_data = m_df['Municipio_Map'].value_counts().reset_index()
            map_data.columns = ['Municipio', 'Registros']
            
            col_map, col_list = st.columns([2, 1])
            
            with col_map:
                try:
                    url = "https://raw.githubusercontent.com/finiterank/mapa-colombia-js/master/colombia-municipios.json"
                    geo = requests.get(url).json()
                    fig = px.choropleth(map_data, geojson=geo, locations='Municipio', featureidkey="properties.name",
                                        color='Registros', color_continuous_scale="Reds", template="plotly_white")
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=500)
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.info("Intentando cargar mapa...")

            with col_list:
                st.write("**Top Municipios**")
                for _, r in map_data.head(6).iterrows():
                    st.markdown(f'<div class="rank-item"><span class="rank-name">{r["Municipio"]}</span><span class="hotspot-pill">{r["Registros"]} regs</span></div>', unsafe_allow_html=True)

            # --- LEADERBOARD ---
            st.markdown("---")
            st.subheader("🏆 Leaderboard de Captación")
            rank = df['Registrado Por'].value_counts().reset_index()
            rank.columns = ['Líder', 'Total']
            cols = st.columns(min(len(rank), 4))
            for i, (idx, row) in enumerate(rank.head(4).iterrows()):
                cols[i].markdown(f"""
                    <div class="rank-item">
                        <div style="display:flex; align-items:center;">
                            <div class="rank-num">{i+1}</div>
                            <span class="rank-name">{str(row['Líder']).upper()}</span>
                        </div>
                        <span class="rank-badge">{row['Total']}</span>
                    </div>
                """, unsafe_allow_html=True)

    elif opcion == "🔍 Búsqueda":
        st.title("🔍 Explorador de Datos")
        df = get_data()
        if not df.empty:
            query = st.text_input("Buscar por nombre, cédula o municipio...").upper()
            if query:
                mask = df.astype(str).apply(lambda x: x.str.upper().str.contains(query)).any(axis=1)
                st.dataframe(df[mask], use_container_width=True)
            else:
                st.dataframe(df.tail(20), use_container_width=True)
